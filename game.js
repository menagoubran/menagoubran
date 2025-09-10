var config = {
    type: Phaser.AUTO,
    width: 800,
    height: 600,
    physics: {
        default: 'arcade',
        arcade: {
            gravity: {y: 500},
            debug: false
        }
    },
    scene: {
        key: 'main',
        preload: preload,
        create: create,
        update: update
    }
};

var game = new Phaser.Game(config);

var map;
var player;
var cursors;
var groundLayer, coinLayer;
var text;
var score = 0;
var ga;
var generationText;
var bestFitnessText;
var distance = 0;
var startTime = 0;

function preload() {
    // map made with Tiled in JSON format
    this.load.tilemapTiledJSON('map', 'assets/map.json');
    // tiles in spritesheet
    this.load.spritesheet('tiles', 'assets/tiles.png', {frameWidth: 70, frameHeight: 70});
    // simple coin image
    this.load.image('coin', 'assets/coinGold.png');
    // player animations
    this.load.spritesheet('player', 'assets/player.png', { frameWidth: 72, frameHeight: 96 });
}

function create() {
    // load the map
    map = this.make.tilemap({key: 'map'});

    // tiles for the ground layer
    var groundTiles = map.addTilesetImage('tiles');
    // create the ground layer
    groundLayer = map.createDynamicLayer('World', groundTiles, 0, 0);
    // the player will collide with this layer
    groundLayer.setCollisionByExclusion([-1]);

    // coin image used as tileset
    var coinTiles = map.addTilesetImage('coin');
    // add coins as tiles
    coinLayer = map.createDynamicLayer('Coins', coinTiles, 0, 0);

    // set the boundaries of our game world
    this.physics.world.bounds.width = groundLayer.width;
    this.physics.world.bounds.height = groundLayer.height;

    // create the player sprite
    player = this.physics.add.sprite(200, 200, 'player');
    player.setBounce(0.2); // our player will bounce from items
    player.setCollideWorldBounds(true); // don't go out of the map

    // small fix to our player images, we resize the physics body object slightly
    player.body.setSize(player.width, player.height-8);

    // player will collide with the level tiles
    this.physics.add.collider(groundLayer, player);

    coinLayer.setTileIndexCallback(17, collectCoin, this);
    // when the player overlaps with a tile with index 17, collectCoin
    // will be called
    this.physics.add.overlap(player, coinLayer);

    // player walk animation
    this.anims.create({
        key: 'walk',
        frames: this.anims.generateFrameNumbers('player', { start: 0, end: 10 }),
        frameRate: 10,
        repeat: -1
    });
    // idle with only one frame, so repeat is not neaded
    this.anims.create({
        key: 'idle',
        frames: [ { key: 'player', frame: 11 } ],
        frameRate: 10,
    });


    cursors = this.input.keyboard.createCursorKeys();

    // set bounds so the camera won't go outside the game world
    this.cameras.main.setBounds(0, 0, map.widthInPixels, map.heightInPixels);
    // make the camera follow the player
    this.cameras.main.startFollow(player);

    // set background color, so the sky is not black
    this.cameras.main.setBackgroundColor('#ccccff');

    //add score text
    text = this.add.text(20, 570, '0', {
        fontSize: '20px',
        fill: '#ffffff'
    });
    text.setScrollFactor(0);

    generationText = this.add.text(20, 20, 'Generation: 0', { fontSize: '20px', fill: '#ffffff' });
    bestFitnessText = this.add.text(20, 50, 'Best Fitness: 0', { fontSize: '20px', fill: '#ffffff' });
    generationText.setScrollFactor(0);
    bestFitnessText.setScrollFactor(0);

    ga = new GeneticAlgorithm(10, 5, 10, 3);
    distance = 0;
    startTime = this.time.now;
}

function update(time, delta) {
    distance = player.x;
    // Get the inputs for the neural network
    let nextCoin = findNextCoin();
    let inputs = [
        player.y / game.config.height,
        nextCoin.dx / game.config.width,
        nextCoin.dy / game.config.height,
        player.body.velocity.x / 1000,
        player.body.velocity.y / 1000
    ];

    // Get the output from the network
    let output = ga.getMove(inputs);

    // Control the player based on the output
    if (output[0] > 0.5) {
        player.body.setVelocityX(-200);
        player.anims.play('walk', true);
        player.flipX = true;
    } else if (output[1] > 0.5) {
        player.body.setVelocityX(200);
        player.anims.play('walk', true);
        player.flipX = false;
    } else {
        player.body.setVelocityX(0);
        player.anims.play('idle', true);
    }

    if (output[2] > 0.5 && player.body.onFloor()) {
        player.body.setVelocityY(-500);
    }

    // Update text elements
    generationText.setText('Generation: ' + ga.generation);
    if(ga.population.bestFitness){
        bestFitnessText.setText('Best Fitness: ' + ga.population.bestFitness.toFixed(2));
    }


    // Restart the game if the player falls off the screen
    if (player.y > game.config.height) {
        ga.runGeneration(score, distance, this.time.now - startTime);
        score = 0;
        this.scene.restart();
    }
}

function collectCoin(sprite, tile) {
    coinLayer.removeTileAt(tile.x, tile.y); // remove the tile/coin
    score++; // increment the score
    text.setText(score); // set the text to show the current score
    return false;
}

function findNextCoin() {
    let coins = coinLayer.getTilesWithinWorldXY(player.x, player.y, game.config.width, game.config.height);
    let closestCoin = null;
    let minDistance = Infinity;

    for (let coin of coins) {
        if (coin.index !== -1) {
            let dx = coin.getCenterX() - player.x;
            let dy = coin.getCenterY() - player.y;
            let distance = Math.sqrt(dx*dx + dy*dy);
            if (distance < minDistance) {
                minDistance = distance;
                closestCoin = coin;
            }
        }
    }

    if (closestCoin) {
        return {
            dx: closestCoin.getCenterX() - player.x,
            dy: closestCoin.getCenterY() - player.y
        };
    } else {
        // No coins left, return some default values
        return { dx: 0, dy: 0 };
    }
}

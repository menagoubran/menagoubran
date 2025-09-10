// A class to represent a neural network
class Network {
    constructor(inputNodes, hiddenNodes, outputNodes) {
        this.inputNodes = inputNodes;
        this.hiddenNodes = hiddenNodes;
        this.outputNodes = outputNodes;

        // Initialize weights and biases
        this.weights_ih = this.randomMatrix(this.hiddenNodes, this.inputNodes);
        this.weights_ho = this.randomMatrix(this.outputNodes, this.hiddenNodes);
        this.bias_h = this.randomMatrix(this.hiddenNodes, 1);
        this.bias_o = this.randomMatrix(this.outputNodes, 1);
    }

    // Create a matrix with random values
    randomMatrix(rows, cols) {
        let matrix = [];
        for (let i = 0; i < rows; i++) {
            matrix[i] = [];
            for (let j = 0; j < cols; j++) {
                matrix[i][j] = Math.random() * 2 - 1; // Random values between -1 and 1
            }
        }
        return matrix;
    }

    // Feed forward the inputs through the network
    feedForward(inputs) {
        // Convert inputs to matrix
        let inputsMatrix = this.arrayToMatrix(inputs);

        // Calculate hidden layer output
        let hidden = this.matrixMultiply(this.weights_ih, inputsMatrix);
        hidden = this.matrixAdd(hidden, this.bias_h);
        hidden = this.matrixMap(hidden, Math.tanh);

        // Calculate output layer output
        let output = this.matrixMultiply(this.weights_ho, hidden);
        output = this.matrixAdd(output, this.bias_o);
        output = this.matrixMap(output, Math.tanh);

        // Convert output matrix to array
        return this.matrixToArray(output);
    }

    // Helper functions for matrix operations
    arrayToMatrix(arr) {
        let matrix = [];
        for (let i = 0; i < arr.length; i++) {
            matrix[i] = [arr[i]];
        }
        return matrix;
    }

    matrixToArray(matrix) {
        let arr = [];
        for (let i = 0; i < matrix.length; i++) {
            arr.push(matrix[i][0]);
        }
        return arr;
    }

    matrixMultiply(a, b) {
        let result = [];
        for (let i = 0; i < a.length; i++) {
            result[i] = [];
            for (let j = 0; j < b[0].length; j++) {
                let sum = 0;
                for (let k = 0; k < a[0].length; k++) {
                    sum += a[i][k] * b[k][j];
                }
                result[i][j] = sum;
            }
        }
        return result;
    }

    matrixAdd(a, b) {
        let result = [];
        for (let i = 0; i < a.length; i++) {
            result[i] = [];
            for (let j = 0; j < a[0].length; j++) {
                result[i][j] = a[i][j] + b[i][j];
            }
        }
        return result;
    }

    matrixMap(matrix, func) {
        let result = [];
        for (let i = 0; i < matrix.length; i++) {
            result[i] = [];
            for (let j = 0; j < matrix[0].length; j++) {
                result[i][j] = func(matrix[i][j]);
            }
        }
        return result;
    }

    // Mutate the network's weights
    mutate(rate) {
        function mutate(val) {
            if (Math.random() < rate) {
                return val + (Math.random() * 2 - 1) * 0.1;
            } else {
                return val;
            }
        }
        this.weights_ih = this.matrixMap(this.weights_ih, mutate);
        this.weights_ho = this.matrixMap(this.weights_ho, mutate);
        this.bias_h = this.matrixMap(this.bias_h, mutate);
        this.bias_o = this.matrixMap(this.bias_o, mutate);
    }

    // Crossover with another network
    crossover(other) {
        let child = new Network(this.inputNodes, this.hiddenNodes, this.outputNodes);

        function crossover(a, b) {
            let mid = Math.floor(Math.random() * a.length);
            let result = [];
            for (let i = 0; i < a.length; i++) {
                result[i] = [];
                for (let j = 0; j < a[0].length; j++) {
                    if (i > mid) {
                        result[i][j] = a[i][j];
                    } else {
                        result[i][j] = b[i][j];
                    }
                }
            }
            return result;
        }

        child.weights_ih = crossover(this.weights_ih, other.weights_ih);
        child.weights_ho = crossover(this.weights_ho, other.weights_ho);
        child.bias_h = crossover(this.bias_h, other.bias_h);
        child.bias_o = crossover(this.bias_o, other.bias_o);

        return child;
    }
}

// A class to represent an agent in the population
class Agent {
    constructor(inputNodes, hiddenNodes, outputNodes) {
        this.network = new Network(inputNodes, hiddenNodes, outputNodes);
        this.fitness = 0;
    }
}


// A class to represent a population of agents
class Population {
    constructor(size, inputNodes, hiddenNodes, outputNodes) {
        this.agents = [];
        for (let i = 0; i < size; i++) {
            this.agents.push(new Agent(inputNodes, hiddenNodes, outputNodes));
        }
        this.matingPool = [];
        this.bestFitness = 0;
    }

    // Evaluate the fitness of all agents in the population
    evaluate(score, distance, time) {
        this.bestFitness = 0;
        for (let agent of this.agents) {
            // A simple fitness function
            agent.fitness = score * 100 + distance + time;
            if (agent.fitness > this.bestFitness) {
                this.bestFitness = agent.fitness;
            }
        }
    }

    // Select the best agents for reproduction
    selection() {
        this.matingPool = [];
        // Tournament selection
        for (let i = 0; i < this.agents.length; i++) {
            let tournamentSize = 5;
            let best = null;
            for (let j = 0; j < tournamentSize; j++) {
                let randomAgent = this.agents[Math.floor(Math.random() * this.agents.length)];
                if (best === null || randomAgent.fitness > best.fitness) {
                    best = randomAgent;
                }
            }
            this.matingPool.push(best);
        }
    }

    // Create a new generation of agents
    reproduction() {
        let newAgents = [];
        for (let i = 0; i < this.agents.length; i++) {
            let parentA = this.matingPool[Math.floor(Math.random() * this.matingPool.length)];
            let parentB = this.matingPool[Math.floor(Math.random() * this.matingPool.length)];
            let child = parentA.network.crossover(parentB.network);
            child.mutate(0.1); // 10% mutation rate
            newAgents.push(new Agent(child.inputNodes, child.hiddenNodes, child.outputNodes));
            newAgents[i].network = child;
        }
        this.agents = newAgents;
    }
}

// The main genetic algorithm class
class GeneticAlgorithm {
    constructor(populationSize, inputNodes, hiddenNodes, outputNodes) {
        this.population = new Population(populationSize, inputNodes, hiddenNodes, outputNodes);
        this.generation = 0;
    }

    // Get the next move from the current agent
    getMove(inputs) {
        // For now, let's just get a move from the first agent
        return this.population.agents[0].network.feedForward(inputs);
    }

    // Run one generation of the genetic algorithm
    runGeneration(score, distance, time) {
        this.population.evaluate(score, distance, time);
        this.population.selection();
        this.population.reproduction();
        this.generation++;
    }
}

#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <ctime>
#include <cstdlib>

using namespace std;

// Structure to represent each treasure category
struct Item {
    string name;
    int id;
    long long q; // quantity
    long long v; // value
    long long m; // mass
    long long l; // volume
};

// Global capacity constraints
const long long MAX_M = 20000000; // 20 kg in mg
const long long MAX_L = 25000000; // 25 L in uL

// Structure to represent a solution state
struct Solution {
    vector<int> counts;
    long long total_v;
    long long total_m;
    long long total_l;

    Solution(int n) : counts(n, 0), total_v(0), total_m(0), total_l(0) {}
};

vector<Item> items;
int N;

// Parse the JSON-like input
void parseInput() {
    string input, line;
    // Read all stdin into a single string
    while (getline(cin, line)) {
        input += line + " ";
    }

    vector<string> tokens;
    string current;
    bool inQuotes = false;
    for (char c : input) {
        if (inQuotes) {
            if (c == '"') {
                inQuotes = false;
                if (!current.empty()) tokens.push_back(current);
                current = "";
            } else {
                current += c;
            }
        } else {
            if (c == '"') {
                inQuotes = true;
            } else if (isdigit(c) || c == '-') {
                current += c;
            } else {
                if (!current.empty()) {
                    tokens.push_back(current);
                    current = "";
                }
            }
        }
    }
    if (!current.empty()) tokens.push_back(current);

    // Tokens are expected in groups of 5: Key, q, v, m, l
    for (size_t i = 0; i < tokens.size(); i += 5) {
        if (i + 4 >= tokens.size()) break;
        Item item;
        item.name = tokens[i];
        item.id = (int)items.size();
        item.q = stoll(tokens[i+1]);
        item.v = stoll(tokens[i+2]);
        item.m = stoll(tokens[i+3]);
        item.l = stoll(tokens[i+4]);
        items.push_back(item);
    }
    N = (int)items.size();
}

// Greedily fill the bag based on a specific item order
void fillGreedy(Solution& sol, const vector<int>& order) {
    for (int idx : order) {
        if (sol.counts[idx] >= items[idx].q) continue;
        
        long long rem_m = MAX_M - sol.total_m;
        long long rem_l = MAX_L - sol.total_l;
        
        if (rem_m < items[idx].m || rem_l < items[idx].l) continue;
        
        long long take_m = rem_m / items[idx].m;
        long long take_l = rem_l / items[idx].l;
        long long take_q = items[idx].q - sol.counts[idx];
        
        long long count = min({take_m, take_l, take_q});
        
        if (count > 0) {
            sol.counts[idx] += count;
            sol.total_v += count * items[idx].v;
            sol.total_m += count * items[idx].m;
            sol.total_l += count * items[idx].l;
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    srand((unsigned)time(NULL));

    parseInput();
    
    if (N == 0) {
        cout << "{}" << endl;
        return 0;
    }

    double start_time = (double)clock() / CLOCKS_PER_SEC;
    
    Solution bestSol(N);
    
    int iterations = 0;
    // Keep trying to improve the solution until time limit approaches
    while (true) {
        iterations++;
        // Check time every 50 iterations to avoid overhead
        if (iterations % 50 == 0) {
            double curr_time = (double)clock() / CLOCKS_PER_SEC;
            if (curr_time - start_time > 0.95) break;
        }

        // Generate a random tradeoff parameter alpha between mass and volume
        double alpha = (double)rand() / RAND_MAX;
        
        // Ensure we test pure Mass and pure Volume heuristics occasionally
        if (iterations == 1) alpha = 0.0;
        else if (iterations == 2) alpha = 1.0;
        else if (iterations == 3) alpha = 0.5;

        // Calculate score for each item based on value per weighted resource usage
        vector<pair<double, int>> density(N);
        for (int i = 0; i < N; ++i) {
            // Normalize costs to capacity to make alpha meaningful
            double w_m = (double)items[i].m / MAX_M;
            double w_l = (double)items[i].l / MAX_L;
            double cost = alpha * w_m + (1.0 - alpha) * w_l;
            if (cost < 1e-15) cost = 1e-15;
            density[i] = { (double)items[i].v / cost, i };
        }
        
        // Sort items by calculated density
        sort(density.rbegin(), density.rend());
        
        vector<int> order;
        for(auto p : density) order.push_back(p.second);
        
        // Construct initial greedy solution
        Solution currSol(N);
        fillGreedy(currSol, order);
        
        // Local Search: "Remove-1-and-Fill" Strategy
        // Try to escape local optima by removing one item and refilling greedily
        bool improved = true;
        while (improved) {
            improved = false;
            Solution localBest = currSol;
            
            for (int i = 0; i < N; ++i) {
                if (currSol.counts[i] > 0) {
                    Solution temp = currSol;
                    // Remove 1 unit of item i
                    temp.counts[i]--;
                    temp.total_v -= items[i].v;
                    temp.total_m -= items[i].m;
                    temp.total_l -= items[i].l;
                    
                    // Try to fill remaining space
                    fillGreedy(temp, order);
                    
                    if (temp.total_v > localBest.total_v) {
                        localBest = temp;
                        improved = true;
                    }
                }
            }
            if (improved) currSol = localBest;
        }

        if (currSol.total_v > bestSol.total_v) {
            bestSol = currSol;
        }
    }
    
    // Output result in JSON format
    cout << "{";
    map<string, int> outMap;
    for(int i=0; i<N; ++i) {
        outMap[items[i].name] = bestSol.counts[i];
    }
    
    bool first = true;
    for (auto const& [key, val] : outMap) {
        if (!first) cout << ",";
        cout << "\n \"" << key << "\": " << val;
        first = false;
    }
    cout << "\n}" << endl;

    return 0;
}
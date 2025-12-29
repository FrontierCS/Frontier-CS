#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <sstream>
#include <random>
#include <chrono>

using namespace std;

// Problem Constants
const long long MAX_MASS_MG = 20000000;
const long long MAX_VOL_UL = 25000000;

struct Item {
    string name;
    int id;
    long long q;
    long long v;
    long long m;
    long long l;
};

// Solution state
struct Solution {
    vector<long long> counts;
    long long current_m;
    long long current_l;
    long long current_v;
    
    Solution(int n) : counts(n, 0), current_m(0), current_l(0), current_v(0) {}
};

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Parse Input
    // Reading all stdin into a string
    string raw_input;
    string line;
    while(getline(cin, line)) {
        raw_input += line + " ";
    }
    
    // Replace JSON delimiters with spaces to simplify parsing
    for(char &c : raw_input) {
        if (c == '{' || c == '}' || c == '[' || c == ']' || c == ',' || c == '"' || c == ':') {
            c = ' ';
        }
    }
    
    stringstream ss(raw_input);
    string key;
    vector<Item> items;
    int id_gen = 0;
    
    // Parse loop
    while(ss >> key) {
        Item item;
        item.name = key;
        item.id = id_gen++;
        if (!(ss >> item.q >> item.v >> item.m >> item.l)) break;
        items.push_back(item);
    }
    
    int N = items.size();
    if (N == 0) {
        cout << "{}" << endl;
        return 0;
    }
    
    // Random engine
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    
    // Track best solution
    long long best_v = -1;
    vector<long long> best_counts(N, 0);
    
    // Time control
    clock_t start_clock = clock();
    double time_limit = 0.95; // Use slightly less than 1.0s to be safe
    
    // Auxiliary vector for item indices
    vector<int> indices(N);
    for(int i=0; i<N; ++i) indices[i] = i;

    // Main Optimization Loop
    while (true) {
        // Check time limit
        if ((double)(clock() - start_clock) / CLOCKS_PER_SEC > time_limit) break;
        
        // 1. Randomized Greedy Construction
        
        // Generate random weights for scoring metric
        uniform_real_distribution<double> dist01(0.0, 1.0);
        double w_mass = dist01(rng);
        
        // Occasionally try pure strategies
        double rand_strat = dist01(rng);
        if (rand_strat < 0.1) w_mass = 1.0;
        else if (rand_strat < 0.2) w_mass = 0.0;
        
        double w_vol = 1.0 - w_mass;
        
        // Rank items
        vector<pair<double, int>> ranked(N);
        for(int i=0; i<N; ++i) {
            double cost = 0;
            // Normalized cost
            if (MAX_MASS_MG > 0) cost += w_mass * ((double)items[i].m / MAX_MASS_MG);
            if (MAX_VOL_UL > 0) cost += w_vol * ((double)items[i].l / MAX_VOL_UL);
            
            if (cost < 1e-15) cost = 1e-15;
            
            double score = (double)items[i].v / cost;
            // Add multiplicative noise to score to explore local variations
            double noise = dist01(rng) * 0.4 + 0.8; // Range [0.8, 1.2]
            ranked[i] = {score * noise, i};
        }
        
        sort(ranked.rbegin(), ranked.rend());
        
        // Fill greedily
        Solution sol(N);
        for(auto& p : ranked) {
            int idx = p.second;
            long long rem_m = MAX_MASS_MG - sol.current_m;
            long long rem_l = MAX_VOL_UL - sol.current_l;
            
            long long count = items[idx].q;
            if (items[idx].m > 0) count = min(count, rem_m / items[idx].m);
            if (items[idx].l > 0) count = min(count, rem_l / items[idx].l);
            
            sol.counts[idx] = count;
            sol.current_m += count * items[idx].m;
            sol.current_l += count * items[idx].l;
            sol.current_v += count * items[idx].v;
        }
        
        // 2. Local Search
        
        // Phase A: Fill Gaps
        // Try to add any item that fits
        shuffle(indices.begin(), indices.end(), rng);
        bool changed = true;
        while(changed) {
            changed = false;
            for(int idx : indices) {
                if (sol.counts[idx] < items[idx].q) {
                    long long rem_m = MAX_MASS_MG - sol.current_m;
                    long long rem_l = MAX_VOL_UL - sol.current_l;
                    
                    long long can_add = items[idx].q - sol.counts[idx];
                    if (items[idx].m > 0) can_add = min(can_add, rem_m / items[idx].m);
                    if (items[idx].l > 0) can_add = min(can_add, rem_l / items[idx].l);
                    
                    if (can_add > 0) {
                        sol.counts[idx] += can_add;
                        sol.current_m += can_add * items[idx].m;
                        sol.current_l += can_add * items[idx].l;
                        sol.current_v += can_add * items[idx].v;
                        changed = true;
                    }
                }
            }
        }
        
        // Phase B: Pairwise Exchange
        // Try to force add item j by removing items of type i
        bool improved = true;
        while(improved) {
            improved = false;
            // Check time inside local search to prevent timeout in edge cases
            if ((double)(clock() - start_clock) / CLOCKS_PER_SEC > time_limit) break;

            for(int i : indices) { // Candidate to remove
                if (sol.counts[i] == 0) continue;
                for(int j : indices) { // Candidate to add
                    if (i == j || sol.counts[j] >= items[j].q) continue;
                    
                    // We want to add at least 1 item of j.
                    long long rem_m = MAX_MASS_MG - sol.current_m;
                    long long rem_l = MAX_VOL_UL - sol.current_l;
                    
                    long long need_m = (items[j].m > rem_m) ? (items[j].m - rem_m) : 0;
                    long long need_l = (items[j].l > rem_l) ? (items[j].l - rem_l) : 0;
                    
                    if (need_m == 0 && need_l == 0) {
                        // Fits without removal (should be handled by gap fill, but safe to have)
                        long long take = 1; 
                        sol.counts[j] += take;
                        sol.current_m += items[j].m;
                        sol.current_l += items[j].l;
                        sol.current_v += items[j].v;
                        improved = true;
                        goto next_iter;
                    }
                    
                    // Calculate minimum items of i to remove to fit 1 j
                    long long remove_i = 0;
                    bool possible = true;
                    
                    if (need_m > 0) {
                        if (items[i].m == 0) { possible = false; }
                        else remove_i = max(remove_i, (need_m + items[i].m - 1) / items[i].m);
                    }
                    if (possible && need_l > 0) {
                        if (items[i].l == 0) { possible = false; }
                        else remove_i = max(remove_i, (need_l + items[i].l - 1) / items[i].l);
                    }
                    
                    if (!possible || remove_i > sol.counts[i]) continue;
                    
                    // Tentative Swap
                    // Remove k items of i
                    long long old_count_i = sol.counts[i];
                    long long old_count_j = sol.counts[j];
                    long long old_m = sol.current_m;
                    long long old_l = sol.current_l;
                    long long old_v = sol.current_v;
                    
                    sol.counts[i] -= remove_i;
                    sol.current_m -= remove_i * items[i].m;
                    sol.current_l -= remove_i * items[i].l;
                    sol.current_v -= remove_i * items[i].v;
                    
                    // Fill with j as much as possible
                    long long can_add_j = items[j].q - sol.counts[j];
                    long long room_m = MAX_MASS_MG - sol.current_m;
                    long long room_l = MAX_VOL_UL - sol.current_l;
                    
                    if (items[j].m > 0) can_add_j = min(can_add_j, room_m / items[j].m);
                    if (items[j].l > 0) can_add_j = min(can_add_j, room_l / items[j].l);
                    
                    if (can_add_j < 1) {
                        // Should not happen if logic is correct, but sanity check
                        // Revert
                        sol.counts[i] = old_count_i;
                        sol.counts[j] = old_count_j;
                        sol.current_m = old_m;
                        sol.current_l = old_l;
                        sol.current_v = old_v;
                        continue;
                    }
                    
                    sol.counts[j] += can_add_j;
                    sol.current_m += can_add_j * items[j].m;
                    sol.current_l += can_add_j * items[j].l;
                    sol.current_v += can_add_j * items[j].v;
                    
                    // Check improvement
                    if (sol.current_v > old_v) {
                        improved = true;
                        goto next_iter;
                    } else {
                        // Revert
                        sol.counts[i] = old_count_i;
                        sol.counts[j] = old_count_j;
                        sol.current_m = old_m;
                        sol.current_l = old_l;
                        sol.current_v = old_v;
                    }
                }
            }
            next_iter:;
        }
        
        // Update Global Best
        if (sol.current_v > best_v) {
            best_v = sol.current_v;
            best_counts = sol.counts;
        }
    }
    
    // Output Result
    cout << "{" << endl;
    for(int i=0; i<N; ++i) {
        cout << " \"" << items[i].name << "\": " << best_counts[i];
        if (i < N - 1) cout << ",";
        cout << endl;
    }
    cout << "}" << endl;

    return 0;
}
#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <chrono>
#include <random>
#include <iomanip>

using namespace std;

// Problem Constants
const long long MAX_MASS = 20000000; // 20 kg in mg
const long long MAX_VOL = 25000000;  // 25 L in uL

struct Item {
    string name;
    int id;
    int q;
    long long v;
    long long m;
    long long l;
};

// Global variables
vector<Item> items;
vector<string> keys_order;
map<string, int> name_to_id;
int N;

// Solution State
vector<int> best_counts;
long long best_total_value = -1;

void parse_input() {
    char c;
    // Skip initial whitespace and opening brace if present
    // The JSON input starts with {
    
    while (cin >> c) {
        if (c == '"') {
            string key = "";
            // Read key until closing quote
            while (cin.get(c) && c != '"') {
                key += c;
            }
            
            // Key found. Expect : then [
            while (cin >> c && c != '[');
            
            // Read array values
            long long q, v, m, l;
            
            // Read q
            cin >> q;
            // Skip to comma
            while (cin >> c && c != ',');
            
            // Read v
            cin >> v;
            // Skip to comma
            while (cin >> c && c != ',');
            
            // Read m
            cin >> m;
            // Skip to comma
            while (cin >> c && c != ',');
            
            // Read l
            cin >> l;
            // Skip to closing bracket
            while (cin >> c && c != ']');
            
            Item item;
            item.name = key;
            item.q = (int)q;
            item.v = v;
            item.m = m;
            item.l = l;
            item.id = items.size();
            
            name_to_id[key] = item.id;
            keys_order.push_back(key);
            items.push_back(item);
        }
    }
    N = items.size();
    best_counts.resize(N, 0);
}

// Timer
auto start_time = chrono::high_resolution_clock::now();

double get_elapsed() {
    auto now = chrono::high_resolution_clock::now();
    return chrono::duration<double>(now - start_time).count();
}

int main() {
    // Fast IO
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    parse_input();
    
    if (N == 0) {
        cout << "{}" << endl;
        return 0;
    }

    // Random number generator
    mt19937 rng(1337);
    uniform_real_distribution<double> dist_real(0.0, 1.0);
    uniform_int_distribution<int> dist_int(0, N - 1);

    // Indices for sorting
    vector<int> p(N);
    for(int i=0; i<N; ++i) p[i] = i;

    // Temporary solution storage
    vector<int> current_counts(N);
    
    // Main optimization loop
    // We run multiple iterations of randomized greedy heuristics
    // Since N=12, we can run many iterations in 1 second.
    while (get_elapsed() < 0.90) {
        
        // Strategy: Randomized Weights for Greedy
        // Generate random weights for mass and volume penalties
        // This corresponds to exploring the dual space of the relaxed LP.
        double w_m = dist_real(rng);
        double w_l = dist_real(rng);
        
        // Occasionally force extreme weights to explore boundaries
        double r = dist_real(rng);
        if (r < 0.05) { w_m = 1.0; w_l = 0.0; }
        else if (r < 0.10) { w_m = 0.0; w_l = 1.0; }
        else if (r < 0.15) { w_m = 1.0; w_l = 1.0; } // Equal weight
        else if (r < 0.20) { w_m = 1.0; w_l = 0.0001; } // Nearly ignore volume
        else if (r < 0.25) { w_m = 0.0001; w_l = 1.0; } // Nearly ignore mass

        // Compute scores and sort
        // Heuristic: Value / Weighted_Cost
        // Cost is normalized by capacity to handle different units
        sort(p.begin(), p.end(), [&](int i, int j) {
            double cost_i = w_m * ((double)items[i].m / MAX_MASS) + w_l * ((double)items[i].l / MAX_VOL);
            double cost_j = w_m * ((double)items[j].m / MAX_MASS) + w_l * ((double)items[j].l / MAX_VOL);
            if (cost_i < 1e-12) cost_i = 1e-12;
            if (cost_j < 1e-12) cost_j = 1e-12;
            return (items[i].v / cost_i) > (items[j].v / cost_j);
        });

        // Current solution state
        long long current_m = 0;
        long long current_l = 0;
        long long current_v = 0;
        fill(current_counts.begin(), current_counts.end(), 0);

        // Perturbation Strategy:
        // Sometimes, force a random item to have a random count (Fix & Fill)
        // This helps escape local optima where greedy dominates.
        bool forced = false;
        int force_idx = -1;
        
        if (dist_real(rng) < 0.3) {
            force_idx = dist_int(rng);
            uniform_int_distribution<int> q_dist(1, items[force_idx].q);
            int force_qty = q_dist(rng);
            
            // Only apply if feasible alone
            if (items[force_idx].m * (long long)force_qty <= MAX_MASS && 
                items[force_idx].l * (long long)force_qty <= MAX_VOL) {
                current_counts[force_idx] = force_qty;
                current_m += items[force_idx].m * force_qty;
                current_l += items[force_idx].l * force_qty;
                current_v += items[force_idx].v * force_qty;
                forced = true;
            }
        }

        // Greedy Fill Phase
        for (int i : p) {
            if (forced && i == force_idx) continue;
            
            long long rem_m = MAX_MASS - current_m;
            long long rem_l = MAX_VOL - current_l;
            
            if (rem_m < 0) rem_m = 0;
            if (rem_l < 0) rem_l = 0;
            
            int can_take_m = (items[i].m == 0) ? items[i].q : (int)(rem_m / items[i].m);
            int can_take_l = (items[i].l == 0) ? items[i].q : (int)(rem_l / items[i].l);
            
            int take = min(items[i].q, min(can_take_m, can_take_l));
            
            // Small mutation: Occasionally take slightly less than max possible
            // to leave space for other items
            if (take > 0 && dist_real(rng) < 0.05) {
                take = max(0, take - 1);
            }

            current_counts[i] = take;
            current_m += (long long)take * items[i].m;
            current_l += (long long)take * items[i].l;
            current_v += (long long)take * items[i].v;
        }
        
        // Gap Filling Phase
        // Iterate through all items again to fill any remaining space
        // This is necessary because the sorted order might have skipped items 
        // that now fit in the small remaining space.
        for (int i = 0; i < N; ++i) {
            if (current_counts[i] < items[i].q) {
                 long long rem_m = MAX_MASS - current_m;
                 long long rem_l = MAX_VOL - current_l;
                 
                 if (items[i].m <= rem_m && items[i].l <= rem_l) {
                     int can_take_m = (items[i].m == 0) ? items[i].q : (int)(rem_m / items[i].m);
                     int can_take_l = (items[i].l == 0) ? items[i].q : (int)(rem_l / items[i].l);
                     int extra = min(items[i].q - current_counts[i], min(can_take_m, can_take_l));
                     
                     current_counts[i] += extra;
                     current_m += (long long)extra * items[i].m;
                     current_l += (long long)extra * items[i].l;
                     current_v += (long long)extra * items[i].v;
                 }
            }
        }

        // Update Global Best
        if (current_v > best_total_value) {
            best_total_value = current_v;
            best_counts = current_counts;
        }
    }

    // Output JSON
    cout << "{" << endl;
    for (size_t i = 0; i < keys_order.size(); ++i) {
        string key = keys_order[i];
        int id = name_to_id[key];
        cout << " \"" << key << "\": " << best_counts[id];
        if (i < keys_order.size() - 1) {
            cout << ",";
        }
        cout << endl;
    }
    cout << "}" << endl;

    return 0;
}
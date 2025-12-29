#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <cmath>
#include <ctime>
#include <random>
#include <climits>

using namespace std;

// Problem constants
const long long MAX_M = 20000000;
const long long MAX_L = 25000000;

struct Item {
    string name;
    int q;
    long long v, m, l;
    int original_index;
};

struct Solution {
    vector<int> counts;
    long long total_v;
    long long total_m;
    long long total_l;
};

vector<Item> items;
vector<string> key_order;
Solution best_sol;

// Parse JSON from stdin
void parse_input() {
    string data;
    char c;
    while (cin.get(c)) data += c;

    size_t n = data.size();
    size_t i = 0;

    while (i < n) {
        // Find start of a key string
        while (i < n && data[i] != '"') i++;
        if (i >= n) break;
        i++; // skip "

        string key = "";
        while (i < n && data[i] != '"') {
            key += data[i];
            i++;
        }
        i++; // skip closing "

        // Search for colon to confirm it's a key
        size_t temp_i = i;
        while (temp_i < n && isspace(data[temp_i])) temp_i++;
        if (temp_i >= n || data[temp_i] != ':') {
            // Not a key-value pair we are interested in (or end of file)
            i = temp_i;
            continue;
        }
        i = temp_i + 1; // skip :

        // Search for array start
        while (i < n && data[i] != '[') i++;
        if (i >= n) break;
        i++; // skip [

        // Parse 4 numbers
        long long vals[4];
        for (int k = 0; k < 4; ++k) {
            while (i < n && !isdigit(data[i])) i++;
            string num_s = "";
            while (i < n && isdigit(data[i])) {
                num_s += data[i];
                i++;
            }
            if (!num_s.empty()) vals[k] = stoll(num_s);
            else vals[k] = 0;
        }

        Item item;
        item.name = key;
        item.q = (int)vals[0];
        item.v = vals[1];
        item.m = vals[2];
        item.l = vals[3];
        item.original_index = items.size();
        
        items.push_back(item);
        key_order.push_back(key);

        // skip until ]
        while (i < n && data[i] != ']') i++;
        i++;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    parse_input();

    int N = items.size();
    if (N == 0) {
        cout << "{}" << endl;
        return 0;
    }

    // Map name to index for easy lookup later
    map<string, int> name_to_idx;
    for (int i = 0; i < N; ++i) {
        name_to_idx[items[i].name] = i;
    }

    // Initialize best solution
    best_sol.counts.assign(N, 0);
    best_sol.total_v = 0;
    best_sol.total_m = 0;
    best_sol.total_l = 0;

    mt19937 rng(12345);
    clock_t start_time = clock();

    // Phase 1: GRASP (Greedy Randomized Adaptive Search Procedure)
    // Run for 40% of allowed time
    while ((double)(clock() - start_time) / CLOCKS_PER_SEC < 0.4) {
        // Random alpha for linear combination of constraints
        double alpha = (double)(rng() % 1001) / 1000.0;
        vector<int> p(N);
        for (int k = 0; k < N; ++k) p[k] = k;

        // Randomized sorting based on value density
        shuffle(p.begin(), p.end(), rng); 
        sort(p.begin(), p.end(), [&](int a, int b) {
            double m_norm_a = (double)items[a].m / MAX_M;
            double l_norm_a = (double)items[a].l / MAX_L;
            double cost_a = alpha * m_norm_a + (1.0 - alpha) * l_norm_a;
            
            double m_norm_b = (double)items[b].m / MAX_M;
            double l_norm_b = (double)items[b].l / MAX_L;
            double cost_b = alpha * m_norm_b + (1.0 - alpha) * l_norm_b;
            
            if (cost_a <= 1e-12) return true;
            if (cost_b <= 1e-12) return false;

            double score_a = items[a].v / cost_a;
            double score_b = items[b].v / cost_b;
            return score_a > score_b;
        });

        Solution curr;
        curr.counts.assign(N, 0);
        curr.total_v = 0;
        curr.total_m = 0;
        curr.total_l = 0;

        for (int idx : p) {
            long long rem_m = MAX_M - curr.total_m;
            long long rem_l = MAX_L - curr.total_l;
            
            int can_take = items[idx].q;
            if (items[idx].m > 0) can_take = min((long long)can_take, rem_m / items[idx].m);
            if (items[idx].l > 0) can_take = min((long long)can_take, rem_l / items[idx].l);
            
            if (can_take > 0) {
                curr.counts[idx] = can_take;
                curr.total_v += (long long)can_take * items[idx].v;
                curr.total_m += (long long)can_take * items[idx].m;
                curr.total_l += (long long)can_take * items[idx].l;
            }
        }

        if (curr.total_v > best_sol.total_v) {
            best_sol = curr;
        }
    }

    // Phase 2: Local Search / Hill Climbing
    // Start from best found in GRASP
    Solution curr = best_sol;
    vector<int> candidates; 
    candidates.reserve(N);

    int iter = 0;
    while (true) {
        iter++;
        // Check time every 1024 iterations
        if ((iter & 1023) == 0) {
            if ((double)(clock() - start_time) / CLOCKS_PER_SEC > 0.98) break;
        }

        Solution next_sol = curr;
        int move_type = rng() % 3;

        if (move_type == 0) { 
            // Move: Add item and Repair if needed
            int idx = rng() % N;
            if (next_sol.counts[idx] < items[idx].q) {
                next_sol.counts[idx]++;
                next_sol.total_v += items[idx].v;
                next_sol.total_m += items[idx].m;
                next_sol.total_l += items[idx].l;

                // Repair if invalid
                while (next_sol.total_m > MAX_M || next_sol.total_l > MAX_L) {
                    candidates.clear();
                    for(int k=0; k<N; ++k) if(next_sol.counts[k] > 0) candidates.push_back(k);
                    if(candidates.empty()) break; 
                    
                    int victim = candidates[rng() % candidates.size()];
                    next_sol.counts[victim]--;
                    next_sol.total_v -= items[victim].v;
                    next_sol.total_m -= items[victim].m;
                    next_sol.total_l -= items[victim].l;
                }
                
                // If valid and not worse, accept
                if (next_sol.total_m <= MAX_M && next_sol.total_l <= MAX_L) {
                    if (next_sol.total_v >= curr.total_v) {
                        curr = next_sol;
                        if (curr.total_v > best_sol.total_v) best_sol = curr;
                    }
                }
            }
        } else if (move_type == 1) {
            // Move: Swap (Add i, Remove j)
            int i = rng() % N;
            int j = rng() % N;
            
            if (i != j && next_sol.counts[i] < items[i].q && next_sol.counts[j] > 0) {
                next_sol.counts[i]++;
                next_sol.total_v += items[i].v;
                next_sol.total_m += items[i].m;
                next_sol.total_l += items[i].l;
                
                next_sol.counts[j]--;
                next_sol.total_v -= items[j].v;
                next_sol.total_m -= items[j].m;
                next_sol.total_l -= items[j].l;
                
                // Only accept if valid and not worse
                if (next_sol.total_m <= MAX_M && next_sol.total_l <= MAX_L) {
                    if (next_sol.total_v >= curr.total_v) {
                        curr = next_sol;
                        if (curr.total_v > best_sol.total_v) best_sol = curr;
                    }
                }
            }
        } else {
            // Move: Fill slack (Add only, valid check immediately)
            int idx = rng() % N;
            if (next_sol.counts[idx] < items[idx].q) {
                if (next_sol.total_m + items[idx].m <= MAX_M && 
                    next_sol.total_l + items[idx].l <= MAX_L) {
                    next_sol.counts[idx]++;
                    next_sol.total_v += items[idx].v;
                    next_sol.total_m += items[idx].m;
                    next_sol.total_l += items[idx].l;
                    
                    curr = next_sol;
                    if (curr.total_v > best_sol.total_v) best_sol = curr;
                }
            }
        }
    }

    // Output JSON
    cout << "{" << endl;
    for (size_t i = 0; i < key_order.size(); ++i) {
        string key = key_order[i];
        int idx = name_to_idx[key];
        cout << " \"" << key << "\": " << best_sol.counts[idx];
        if (i < key_order.size() - 1) cout << ",";
        cout << endl;
    }
    cout << "}" << endl;

    return 0;
}
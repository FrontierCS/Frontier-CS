#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <ctime>
#include <cstdlib>
#include <random>
#include <chrono>

using namespace std;

const long long MAX_M = 20000000; // 20 kg in mg
const long long MAX_L = 25000000; // 25 L in uL

struct Item {
    string name;
    int id;
    int q;
    long long v, m, l;
};

struct Solution {
    vector<int> counts;
    long long total_v;
    long long total_m;
    long long total_l;

    Solution(int n) : counts(n, 0), total_v(0), total_m(0), total_l(0) {}

    // Try to add one unit of item idx
    bool add(int idx, const vector<Item>& items) {
        if (counts[idx] >= items[idx].q) return false;
        if (total_m + items[idx].m > MAX_M) return false;
        if (total_l + items[idx].l > MAX_L) return false;
        counts[idx]++;
        total_v += items[idx].v;
        total_m += items[idx].m;
        total_l += items[idx].l;
        return true;
    }

    // Try to remove one unit of item idx
    bool remove(int idx, const vector<Item>& items) {
        if (counts[idx] <= 0) return false;
        counts[idx]--;
        total_v -= items[idx].v;
        total_m -= items[idx].m;
        total_l -= items[idx].l;
        return true;
    }
    
    // Fill remaining space with items in order of p
    void fill(const vector<Item>& items, const vector<int>& p) {
        for (int idx : p) {
            long long rem_m = MAX_M - total_m;
            long long rem_l = MAX_L - total_l;
            
            long long count_by_m = (items[idx].m == 0) ? items[idx].q : rem_m / items[idx].m;
            long long count_by_l = (items[idx].l == 0) ? items[idx].q : rem_l / items[idx].l;
            
            int take = (int)min((long long)(items[idx].q - counts[idx]), min(count_by_m, count_by_l));
            
            if (take > 0) {
                counts[idx] += take;
                total_v += (long long)take * items[idx].v;
                total_m += (long long)take * items[idx].m;
                total_l += (long long)take * items[idx].l;
            }
        }
    }
};

vector<Item> items;
int N;

void parse_input() {
    string s, line;
    while (getline(cin, line)) s += line;
    
    // Remove whitespace
    string clean;
    clean.reserve(s.size());
    for (char c : s) if (!isspace(c)) clean += c;
    s = clean;

    size_t pos = 1; // skip '{'
    while (pos < s.length() && s[pos] != '}') {
        if (s[pos] == ',') { pos++; continue; }
        if (s[pos] == '"') {
            size_t end_quote = s.find('"', pos + 1);
            string key = s.substr(pos + 1, end_quote - pos - 1);
            pos = end_quote + 1;
            if (s[pos] == ':') pos++;
            if (s[pos] == '[') pos++;
            
            Item item;
            item.name = key;
            item.id = items.size();
            
            for (int i = 0; i < 4; ++i) {
                size_t next_comma = s.find_first_of(",]", pos);
                string num_str = s.substr(pos, next_comma - pos);
                long long val = stoll(num_str);
                if (i == 0) item.q = (int)val;
                else if (i == 1) item.v = val;
                else if (i == 2) item.m = val;
                else if (i == 3) item.l = val;
                pos = next_comma + 1;
            }
            items.push_back(item);
        } else {
            pos++;
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    parse_input();
    N = items.size();
    
    unsigned seed = std::chrono::system_clock::now().time_since_epoch().count();
    std::default_random_engine generator(seed);
    std::uniform_real_distribution<double> dist(0.0, 1.0);
    srand(seed);

    Solution best_sol(N);
    
    clock_t start_time = clock();
    // Use 0.9 seconds to stay safe within 1s limit
    double time_limit = 0.9; 

    auto solve_heuristic = [&](double alpha, double beta, bool rand_perturb) {
        vector<int> p(N);
        for(int i=0; i<N; ++i) p[i] = i;
        
        sort(p.begin(), p.end(), [&](int a, int b) {
            double wa = (double)items[a].v / (alpha * items[a].m + beta * items[a].l + 1e-9);
            double wb = (double)items[b].v / (alpha * items[b].m + beta * items[b].l + 1e-9);
            if (rand_perturb) {
                // Slightly randomize the density to break ties or explore neighbors
                wa *= (0.95 + 0.1 * dist(generator));
                wb *= (0.95 + 0.1 * dist(generator));
            }
            return wa > wb;
        });
        
        Solution cur(N);
        cur.fill(items, p);
        
        // Local Search / Hill Climbing
        bool improved = true;
        while (improved) {
            improved = false;
            
            // 1. Try adding items that fit
            for (int i = 0; i < N; ++i) {
                if (cur.add(i, items)) {
                    improved = true;
                    while(cur.add(i, items));
                }
            }
            
            // 2. Try swapping: remove 1 item, fill with others
            vector<int> check_order(N);
            for(int k=0; k<N; ++k) check_order[k] = k;
            std::shuffle(check_order.begin(), check_order.end(), generator);
            
            for (int i : check_order) {
                if (cur.counts[i] > 0) {
                    cur.remove(i, items);
                    long long val_prev = cur.total_v + items[i].v;
                    
                    // Try filling with current heuristic order p
                    Solution temp = cur;
                    temp.fill(items, p);
                    
                    if (temp.total_v > val_prev) {
                        cur = temp;
                        improved = true;
                        break; 
                    } else {
                        cur.add(i, items); // Revert
                    }
                }
            }
        }
        
        if (cur.total_v > best_sol.total_v) {
            best_sol = cur;
        }
    };

    // 1. Deterministic Sweeps
    for (int i = 0; i <= 20; ++i) {
        double alpha = i / 20.0;
        solve_heuristic(alpha, 1.0 - alpha, false);
        solve_heuristic(alpha, 1.0, false);
        solve_heuristic(1.0, alpha, false);
    }
    
    // 2. Randomized Search + Iterated Greedy
    while ((double)(clock() - start_time) / CLOCKS_PER_SEC < time_limit) {
        // Random Weights from scratch
        double alpha = dist(generator);
        double beta = dist(generator);
        solve_heuristic(alpha, beta, true);
        
        // Iterated Greedy: Perturb best solution
        if (best_sol.total_v > 0) {
            Solution cur = best_sol;
            
            // Remove random parts
            int types_to_reduce = 1 + rand() % 4;
            for(int k=0; k<types_to_reduce; ++k) {
                int idx = rand() % N;
                if (cur.counts[idx] > 0) {
                    int remove_cnt = 1 + rand() % (max(1, cur.counts[idx]/2) + 1);
                    for(int r=0; r<remove_cnt; ++r) cur.remove(idx, items);
                }
            }
            
            // Generate random weights for refill
            double a = dist(generator);
            double b = dist(generator);
            vector<int> p(N);
            for(int i=0; i<N; ++i) p[i] = i;
            sort(p.begin(), p.end(), [&](int x, int y) {
                double wx = (double)items[x].v / (a * items[x].m + b * items[x].l + 1e-9);
                double wy = (double)items[y].v / (a * items[y].m + b * items[y].l + 1e-9);
                return wx > wy;
            });
            
            cur.fill(items, p);
            
            // Improve
            bool improved = true;
            while (improved) {
                improved = false;
                for (int i = 0; i < N; ++i) {
                    if (cur.add(i, items)) {
                        improved = true;
                        while(cur.add(i, items));
                    }
                }
                vector<int> check_order(N);
                for(int k=0; k<N; ++k) check_order[k] = k;
                std::shuffle(check_order.begin(), check_order.end(), generator);
                for (int i : check_order) {
                    if (cur.counts[i] > 0) {
                        cur.remove(i, items);
                        long long val_prev = cur.total_v + items[i].v;
                        Solution temp = cur;
                        temp.fill(items, p);
                        if (temp.total_v > val_prev) {
                            cur = temp;
                            improved = true;
                            break; 
                        } else {
                            cur.add(i, items);
                        }
                    }
                }
            }
            if (cur.total_v > best_sol.total_v) best_sol = cur;
        }
    }

    // Output
    vector<int> out_order(N);
    for(int i=0; i<N; ++i) out_order[i] = i;
    sort(out_order.begin(), out_order.end(), [&](int a, int b){
        return items[a].name < items[b].name;
    });

    cout << "{";
    for (size_t k = 0; k < out_order.size(); ++k) {
        int idx = out_order[k];
        cout << "\n \"" << items[idx].name << "\": " << best_sol.counts[idx];
        if (k < out_order.size() - 1) cout << ",";
        else cout << "\n";
    }
    cout << "}" << endl;

    return 0;
}
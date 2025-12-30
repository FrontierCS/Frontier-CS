#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <sstream>
#include <cmath>
#include <ctime>

using namespace std;

// Data Structures
struct ItemType {
    string id;
    int w, h;
    long long v;
    int limit;
    int original_idx;
};

struct Rect {
    int x, y, w, h;
    bool operator==(const Rect& other) const {
        return x == other.x && y == other.y && w == other.w && h == other.h;
    }
};

struct Placement {
    int type_idx;
    int x, y;
    int rot; 
};

struct Solution {
    vector<Placement> placements;
    long long total_value;
};

// Global Problem Variables
int W, H;
bool allow_rotate;
vector<ItemType> items;
Solution best_sol;
vector<Rect> free_rects;

// JSON Parsing Helper Variables
string input_str;
size_t pos_idx = 0;

// Helper Functions
void skip_ws() {
    while (pos_idx < input_str.length() && isspace(input_str[pos_idx])) pos_idx++;
}

long long parse_int() {
    skip_ws();
    size_t next_pos;
    long long val = stoll(input_str.substr(pos_idx), &next_pos);
    pos_idx += next_pos;
    return val;
}

string parse_string() {
    skip_ws();
    if (pos_idx < input_str.length() && input_str[pos_idx] == '"') pos_idx++;
    string s;
    while (pos_idx < input_str.length() && input_str[pos_idx] != '"') {
        s += input_str[pos_idx];
        pos_idx++;
    }
    if (pos_idx < input_str.length()) pos_idx++; // skip closing quote
    return s;
}

bool parse_bool() {
    skip_ws();
    if (input_str.compare(pos_idx, 4, "true") == 0) { pos_idx += 4; return true; }
    if (input_str.compare(pos_idx, 5, "false") == 0) { pos_idx += 5; return false; }
    return false;
}

void find_key(string key) {
    string qkey = "\"" + key + "\"";
    size_t found = input_str.find(qkey, pos_idx);
    if (found != string::npos) {
        pos_idx = found + qkey.length();
        skip_ws();
        if (input_str[pos_idx] == ':') pos_idx++;
    }
}

// Geometry Logic
bool is_contained(const Rect& inner, const Rect& outer) {
    return inner.x >= outer.x && inner.y >= outer.y &&
           inner.x + inner.w <= outer.x + outer.w &&
           inner.y + inner.h <= outer.y + outer.h;
}

bool intersect(const Rect& a, const Rect& b) {
    return a.x < b.x + b.w && a.x + a.w > b.x &&
           a.y < b.y + b.h && a.y + a.h > b.y;
}

// Maximal Rectangles Update
void split_free_rects(const Rect& p) {
    vector<Rect> next_free;
    next_free.reserve(free_rects.size() * 2 + 10);

    for (const auto& fr : free_rects) {
        // If disjoint, keep it
        if (!intersect(fr, p)) {
            next_free.push_back(fr);
            continue;
        }
        
        // Split
        if (fr.y + fr.h > p.y + p.h) 
            next_free.push_back({fr.x, p.y + p.h, fr.w, fr.y + fr.h - (p.y + p.h)});
        if (fr.y < p.y) 
            next_free.push_back({fr.x, fr.y, fr.w, p.y - fr.y});
        if (fr.x < p.x) 
            next_free.push_back({fr.x, fr.y, p.x - fr.x, fr.h});
        if (fr.x + fr.w > p.x + p.w) 
            next_free.push_back({p.x + p.w, fr.y, fr.x + fr.w - (p.x + p.w), fr.h});
    }

    // Remove duplicates
    sort(next_free.begin(), next_free.end(), [](const Rect& a, const Rect& b){
        if (a.x != b.x) return a.x < b.x;
        if (a.y != b.y) return a.y < b.y;
        if (a.w != b.w) return a.w < b.w;
        return a.h < b.h;
    });
    next_free.erase(unique(next_free.begin(), next_free.end()), next_free.end());

    // Filter contained rectangles
    free_rects.clear();
    free_rects.reserve(next_free.size());
    
    for (size_t i = 0; i < next_free.size(); ++i) {
        bool dominated = false;
        for (size_t j = 0; j < next_free.size(); ++j) {
            if (i == j) continue;
            if (is_contained(next_free[i], next_free[j])) {
                dominated = true;
                break;
            }
        }
        if (!dominated) free_rects.push_back(next_free[i]);
    }
}

// Random Utilities
unsigned int rng_state = 12345;
int my_rand() {
    rng_state = rng_state * 1664525 + 1013904223;
    return (rng_state >> 16) & 0x7FFF;
}
double rand_double() { return my_rand() / 32768.0; }

// Strategy Params
struct Params {
    double val_pow, dens_pow, fit_pow;
};

// Heuristic Scoring
double score_item(const ItemType& item, const Rect& free_r, bool rot, const Params& p) {
    int iw = rot ? item.h : item.w;
    int ih = rot ? item.w : item.h;
    
    // Check fit
    if (iw > free_r.w || ih > free_r.h) return -1.0;
    
    double density = (double)item.v / (item.w * item.h);
    double w_ratio = (double)iw / free_r.w;
    double h_ratio = (double)ih / free_r.h;
    double fit = w_ratio * h_ratio; 
    
    return pow((double)item.v, p.val_pow) * pow(density, p.dens_pow) * pow(fit, p.fit_pow);
}

// Greedy Solver using Maximal Rectangles + Bottom-Left choice
void run_greedy(Params p) {
    free_rects.clear();
    free_rects.push_back({0, 0, W, H});
    vector<int> limits(items.size());
    for(size_t i=0; i<items.size(); ++i) limits[i] = items[i].limit;
    
    Solution sol;
    sol.total_value = 0;
    
    while(!free_rects.empty()) {
        // 1. Select Free Rect: Deepest Bottom-Left
        int best_r_idx = -1;
        int min_y = 2000000000, min_x = 2000000000;
        
        for (int i = 0; i < (int)free_rects.size(); ++i) {
            if (free_rects[i].y < min_y || (free_rects[i].y == min_y && free_rects[i].x < min_x)) {
                min_y = free_rects[i].y;
                min_x = free_rects[i].x;
                best_r_idx = i;
            }
        }
        
        if (best_r_idx == -1) break; // Should not happen if not empty
        Rect target = free_rects[best_r_idx];
        
        // 2. Select Best Item for this Rect
        int best_item_idx = -1;
        int best_rot = 0;
        double best_score = -1.0;
        
        for (int i = 0; i < (int)items.size(); ++i) {
            if (limits[i] <= 0) continue;
            
            // Orientation 0
            double s0 = score_item(items[i], target, false, p);
            if (s0 > best_score) {
                best_score = s0;
                best_item_idx = i;
                best_rot = 0;
            }
            
            // Orientation 1
            if (allow_rotate && items[i].w != items[i].h) {
                double s1 = score_item(items[i], target, true, p);
                if (s1 > best_score) {
                    best_score = s1;
                    best_item_idx = i;
                    best_rot = 1;
                }
            }
        }
        
        if (best_item_idx != -1) {
            int iw = (best_rot == 1) ? items[best_item_idx].h : items[best_item_idx].w;
            int ih = (best_rot == 1) ? items[best_item_idx].w : items[best_item_idx].h;
            
            sol.placements.push_back({best_item_idx, target.x, target.y, best_rot});
            sol.total_value += items[best_item_idx].v;
            limits[best_item_idx]--;
            
            split_free_rects({target.x, target.y, iw, ih});
        } else {
            // Cannot fill this free rect (too small for any remaining item)
            // Remove it to uncover others or proceed
            free_rects.erase(free_rects.begin() + best_r_idx);
        }
    }
    
    if (sol.total_value > best_sol.total_value) {
        best_sol = sol;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Read Input into string
    string line;
    while(getline(cin, line)) input_str += line;
    
    // Parse JSON
    find_key("bin");
    find_key("W"); W = (int)parse_int();
    find_key("H"); H = (int)parse_int();
    find_key("allow_rotate"); allow_rotate = parse_bool();
    
    find_key("items");
    while(pos_idx < input_str.length() && input_str[pos_idx] != '[') pos_idx++;
    pos_idx++; // skip '['
    
    int idx_counter = 0;
    while(true) {
        skip_ws();
        if(pos_idx >= input_str.length() || input_str[pos_idx] == ']') break;
        if(input_str[pos_idx] == ',') { pos_idx++; continue; }
        if(input_str[pos_idx] == '{') {
            ItemType it;
            it.original_idx = idx_counter++;
            while(pos_idx < input_str.length() && input_str[pos_idx] != '}') {
                string key = parse_string();
                skip_ws();
                if(input_str[pos_idx] == ':') pos_idx++;
                
                if(key == "type") it.id = parse_string();
                else if(key == "w") it.w = (int)parse_int();
                else if(key == "h") it.h = (int)parse_int();
                else if(key == "v") it.v = parse_int();
                else if(key == "limit") it.limit = (int)parse_int();
                
                skip_ws();
                if(input_str[pos_idx] == ',') pos_idx++;
            }
            items.push_back(it);
            pos_idx++; // skip '}'
        } else pos_idx++;
    }
    
    best_sol.total_value = 0;
    
    // Optimization Loop
    double time_limit = 0.95;
    clock_t start_time = clock();
    
    // Heuristic Configurations
    vector<Params> strategies;
    strategies.push_back({1.0, 0.0, 0.0}); // Greedy Value
    strategies.push_back({0.0, 1.0, 0.0}); // Greedy Density
    strategies.push_back({0.0, 1.0, 1.0}); // Density * Fit
    strategies.push_back({1.0, 0.0, 1.0}); // Value * Fit
    strategies.push_back({1.0, 1.0, 0.0}); // Value * Density
    strategies.push_back({2.0, 1.0, 0.0});
    strategies.push_back({1.0, 2.0, 0.0});
    
    int strat_idx = 0;
    while (true) {
        double elapsed = (double)(clock() - start_time) / CLOCKS_PER_SEC;
        if (elapsed > time_limit) break;
        
        Params p;
        if (strat_idx < strategies.size()) {
            p = strategies[strat_idx++];
        } else {
            // Randomized Search
            p.val_pow = rand_double() * 4.0;
            p.dens_pow = rand_double() * 4.0;
            p.fit_pow = rand_double() * 2.0;
        }
        
        run_greedy(p);
    }
    
    // Output JSON
    cout << "{\"placements\":[";
    for(size_t i=0; i<best_sol.placements.size(); ++i) {
        const auto& pl = best_sol.placements[i];
        cout << "{\"type\":\"" << items[pl.type_idx].id << "\","
             << "\"x\":" << pl.x << ","
             << "\"y\":" << pl.y << ","
             << "\"rot\":" << pl.rot << "}";
        if(i < best_sol.placements.size() - 1) cout << ",";
    }
    cout << "]}" << endl;

    return 0;
}
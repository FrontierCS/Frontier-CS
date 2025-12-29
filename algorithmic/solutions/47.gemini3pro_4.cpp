#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>
#include <ctime>
#include <cstdlib>

using namespace std;

// --- JSON Parsing Helpers ---

struct Token {
    string type; // "STR", "NUM", "BOOL", "SYM"
    string value;
};

vector<Token> tokenize(const string& json) {
    vector<Token> tokens;
    int n = json.length();
    for (int i = 0; i < n; ++i) {
        char c = json[i];
        if (isspace(c)) continue;
        if (c == '{' || c == '}' || c == '[' || c == ']' || c == ':' || c == ',') {
            tokens.push_back({"SYM", string(1, c)});
        } else if (c == '"') {
            string s;
            i++;
            while (i < n && json[i] != '"') {
                s += json[i];
                i++;
            }
            tokens.push_back({"STR", s});
        } else if (isdigit(c) || c == '-') {
            string s;
            s += c;
            while (i + 1 < n && (isdigit(json[i+1]) || json[i+1] == '.')) {
                s += json[++i];
            }
            tokens.push_back({"NUM", s});
        } else if (isalpha(c)) {
            string s;
            s += c;
            while (i + 1 < n && isalpha(json[i+1])) {
                s += json[++i];
            }
            tokens.push_back({ (s=="true"||s=="false") ? "BOOL" : "STR", s});
        }
    }
    return tokens;
}

// --- Problem Structures ---

struct ItemType {
    string id;
    int w, h, v, limit;
};

struct Placement {
    string type_id;
    int x, y, rot;
};

struct Rect {
    int x, y, w, h;
    long long area() const { return (long long)w * h; }
};

// --- Globals ---

int bin_W = 0, bin_H = 0;
bool allow_rotate = false;
vector<ItemType> item_types;

// --- Parser Logic ---

void parse_input() {
    string json_str, line;
    while (getline(cin, line)) json_str += line;
    
    vector<Token> tokens = tokenize(json_str);
    size_t idx = 0;
    
    while (idx < tokens.size()) {
        if (tokens[idx].type == "STR") {
            if (tokens[idx].value == "bin") {
                idx++; // skip "bin"
                // expect : {
                while (idx < tokens.size() && tokens[idx].value != "{") idx++;
                if(idx < tokens.size()) idx++; // enter {
                
                int brace_depth = 1;
                while (idx < tokens.size() && brace_depth > 0) {
                    if (tokens[idx].value == "}") { brace_depth--; idx++; continue; }
                    if (tokens[idx].value == "{") { brace_depth++; idx++; continue; }
                    
                    if (tokens[idx].type == "STR") {
                        string key = tokens[idx].value;
                        if (idx + 2 < tokens.size()) {
                            if (key == "W") bin_W = stoi(tokens[idx+2].value);
                            else if (key == "H") bin_H = stoi(tokens[idx+2].value);
                            else if (key == "allow_rotate") allow_rotate = (tokens[idx+2].value == "true");
                        }
                    }
                    idx++;
                }
            } else if (tokens[idx].value == "items") {
                while (idx < tokens.size() && tokens[idx].value != "[") idx++;
                if(idx < tokens.size()) idx++; // enter [
                
                while (idx < tokens.size() && tokens[idx].value != "]") {
                    if (tokens[idx].value == "{") {
                        ItemType it;
                        it.w = 0; it.h = 0; it.v = 0; it.limit = 0;
                        
                        int brace_depth = 1;
                        idx++;
                        while (idx < tokens.size() && brace_depth > 0) {
                            if (tokens[idx].value == "}") { brace_depth--; if(brace_depth==0) break; }
                            if (tokens[idx].value == "{") { brace_depth++; }
                            
                            if (tokens[idx].type == "STR") {
                                string key = tokens[idx].value;
                                if (idx + 2 < tokens.size()) {
                                    if (key == "type") it.id = tokens[idx+2].value;
                                    else if (key == "w") it.w = stoi(tokens[idx+2].value);
                                    else if (key == "h") it.h = stoi(tokens[idx+2].value);
                                    else if (key == "v") it.v = stoi(tokens[idx+2].value);
                                    else if (key == "limit") it.limit = stoi(tokens[idx+2].value);
                                }
                            }
                            idx++;
                        }
                        item_types.push_back(it);
                    }
                    idx++;
                }
            }
        }
        idx++;
    }
}

// --- Solver Logic ---

bool can_fit(const Rect& r, int w, int h) {
    return w <= r.w && h <= r.h;
}

vector<Placement> best_sol;
long long max_profit_found = -1;

void solve() {
    double time_limit = 0.95;
    clock_t start = clock();
    
    // Iterative randomized greedy approach
    do {
        // Randomize strategy for this iteration
        int score_mode = rand() % 6; 
        int split_mode = rand() % 6;
        // score_mode: 0=Value, 1=Density, 2=Val*Fit, 3=Dens*Fit, 4=Val*Fit^2, 5=Area
        // split_mode: 0=ShortAxis, 1=LongAxis, 2=MaxArea, 3=MinArea, 4=Vert, 5=Horz
        
        vector<int> counts(item_types.size());
        for(size_t i=0; i<item_types.size(); ++i) counts[i] = item_types[i].limit;
        
        vector<Rect> free_rects;
        free_rects.push_back({0, 0, bin_W, bin_H});
        
        vector<Placement> current_sol;
        long long current_profit = 0;
        
        bool placed_something = true;
        while (placed_something) {
            placed_something = false;
            
            int best_r = -1;
            int best_t = -1;
            int best_rot = 0;
            double best_score = -1.0;
            
            // Check all FreeRect x ItemType pairs
            for (int r = 0; r < (int)free_rects.size(); ++r) {
                const Rect& fr = free_rects[r];
                for (int t = 0; t < (int)item_types.size(); ++t) {
                    if (counts[t] <= 0) continue;
                    const ItemType& it = item_types[t];
                    
                    int rots = (allow_rotate && it.w != it.h) ? 2 : 1;
                    
                    for (int rot = 0; rot < rots; ++rot) {
                        int iw = (rot == 0) ? it.w : it.h;
                        int ih = (rot == 0) ? it.h : it.w;
                        
                        if (can_fit(fr, iw, ih)) {
                            double score = 0;
                            double item_area = (double)iw * ih;
                            double rect_area = (double)fr.w * fr.h;
                            double tight = item_area / rect_area;
                            
                            if (score_mode == 0) score = it.v;
                            else if (score_mode == 1) score = (double)it.v / item_area;
                            else if (score_mode == 2) score = it.v * tight;
                            else if (score_mode == 3) score = ((double)it.v / item_area) * tight;
                            else if (score_mode == 4) score = it.v * tight * tight; 
                            else if (score_mode == 5) score = item_area; 
                            
                            // Random noise (1.00 to 1.02)
                            double noise = 1.0 + (rand() % 1000) / 50000.0;
                            score *= noise;
                            
                            if (score > best_score) {
                                best_score = score;
                                best_r = r;
                                best_t = t;
                                best_rot = rot;
                            }
                        }
                    }
                }
            }
            
            if (best_r != -1) {
                placed_something = true;
                const Rect& fr = free_rects[best_r];
                const ItemType& it = item_types[best_t];
                
                int iw = (best_rot == 0) ? it.w : it.h;
                int ih = (best_rot == 0) ? it.h : it.w;
                
                current_sol.push_back({it.id, fr.x, fr.y, best_rot});
                current_profit += it.v;
                counts[best_t]--;
                
                // Guillotine Split
                Rect new_r1 = {0,0,0,0}, new_r2 = {0,0,0,0};
                bool split_horz = false;
                
                int rw = fr.w - iw; // Remaining width
                int rh = fr.h - ih; // Remaining height
                
                // Heuristic for split direction
                if (split_mode == 0) { // Shorter Axis
                    if (rw < rh) split_horz = true; else split_horz = false;
                } else if (split_mode == 1) { // Longer Axis
                    if (rw > rh) split_horz = true; else split_horz = false;
                } else if (split_mode == 2) { // Maximize Larger Area
                    long long area_h = max((long long)fr.w * rh, (long long)rw * ih);
                    long long area_v = max((long long)rw * fr.h, (long long)iw * rh);
                    if (area_h > area_v) split_horz = true; else split_horz = false;
                } else if (split_mode == 3) { // Maximize Smaller Area (Min Area)
                    long long area_h = min((long long)fr.w * rh, (long long)rw * ih);
                    long long area_v = min((long long)rw * fr.h, (long long)iw * rh);
                    if (area_h > area_v) split_horz = true; else split_horz = false;
                } else if (split_mode == 4) split_horz = false; // Vertical
                else split_horz = true; // Horizontal
                
                if (split_horz) {
                    // Horizontal cut: Top rect (full width), Right rect (item height)
                    new_r1 = {fr.x, fr.y + ih, fr.w, rh}; 
                    new_r2 = {fr.x + iw, fr.y, rw, ih};   
                } else {
                    // Vertical cut: Right rect (full height), Top rect (item width)
                    new_r1 = {fr.x + iw, fr.y, rw, fr.h}; 
                    new_r2 = {fr.x, fr.y + ih, iw, rh};   
                }
                
                // Update free_rects: remove used, add new
                free_rects[best_r] = free_rects.back();
                free_rects.pop_back();
                
                if (new_r1.w > 0 && new_r1.h > 0) free_rects.push_back(new_r1);
                if (new_r2.w > 0 && new_r2.h > 0) free_rects.push_back(new_r2);
            }
        }
        
        if (current_profit > max_profit_found) {
            max_profit_found = current_profit;
            best_sol = current_sol;
        }
        
    } while ((double)(clock() - start) / CLOCKS_PER_SEC < time_limit);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    srand(time(NULL) ^ clock());
    
    parse_input();
    
    if (bin_W > 0 && bin_H > 0 && !item_types.empty()) {
        solve();
    }
    
    cout << "{\"placements\": [";
    for (size_t i = 0; i < best_sol.size(); ++i) {
        cout << "{\"type\":\"" << best_sol[i].type_id << "\",\"x\":" << best_sol[i].x 
             << ",\"y\":" << best_sol[i].y << ",\"rot\":" << best_sol[i].rot << "}";
        if (i != best_sol.size() - 1) cout << ",";
    }
    cout << "]}" << endl;
    
    return 0;
}
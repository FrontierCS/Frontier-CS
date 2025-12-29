#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <chrono>
#include <cmath>
#include <deque>

using namespace std;

// ==============================================================================================
// DATA STRUCTURES
// ==============================================================================================

struct ItemType {
    string id;
    int w, h;
    long long v;
    int limit;
};

struct Bin {
    int W, H;
    bool allow_rotate;
};

struct Input {
    Bin bin;
    vector<ItemType> items;
};

struct Placement {
    string type_id;
    int x, y, rot;
};

struct Rect {
    int x, y, w, h;
};

struct ItemInst {
    int type_idx;
    int w, h;
    long long v;
    string id;
};

struct Solution {
    vector<Placement> placements;
    long long total_profit = 0;
};

// ==============================================================================================
// JSON PARSER
// ==============================================================================================

Input parseInput(const string& src) {
    Input in;
    size_t pos = 0;
    auto peek = [&]() -> char {
        while(pos < src.size() && isspace(src[pos])) pos++;
        return (pos < src.size()) ? src[pos] : 0;
    };
    auto get = [&]() -> char { char c = peek(); if(pos < src.size()) pos++; return c; };
    auto expect = [&](char c) { if(peek() == c) pos++; };
    auto parseString = [&]() -> string {
        expect('"');
        string s;
        while(pos < src.size()) {
            if(src[pos] == '"') { pos++; break; }
            s += src[pos++];
        }
        return s;
    };
    auto parseInt = [&]() -> long long {
        peek();
        size_t start = pos;
        if(pos < src.size() && src[pos] == '-') pos++;
        while(pos < src.size() && isdigit(src[pos])) pos++;
        return stoll(src.substr(start, pos - start));
    };
    auto parseBool = [&]() -> bool {
        peek();
        if(src.substr(pos, 4) == "true") { pos += 4; return true; }
        if(src.substr(pos, 5) == "false") { pos += 5; return false; }
        return false;
    };
    auto skipValue = [&](auto& self) -> void {
        char c = peek();
        if(c == '{') {
            get();
            while(peek() != '}') {
                parseString(); expect(':'); self(self);
                if(peek() == ',') get();
            }
            get();
        } else if(c == '[') {
            get();
            while(peek() != ']') {
                self(self);
                if(peek() == ',') get();
            }
            get();
        } else if(c == '"') {
            parseString();
        } else {
             while(pos < src.size() && (isalnum(src[pos]) || src[pos] == '-')) pos++;
        }
    };

    expect('{');
    while(peek() != '}') {
        string key = parseString();
        expect(':');
        if(key == "bin") {
            expect('{');
            while(peek() != '}') {
                string bk = parseString();
                expect(':');
                if(bk == "W") in.bin.W = (int)parseInt();
                else if(bk == "H") in.bin.H = (int)parseInt();
                else if(bk == "allow_rotate") in.bin.allow_rotate = parseBool();
                else skipValue(skipValue);
                if(peek() == ',') get();
            }
            get();
        } else if(key == "items") {
            expect('[');
            while(peek() != ']') {
                ItemType it;
                it.w = 0; it.h = 0; it.v = 0; it.limit = 0; 
                expect('{');
                while(peek() != '}') {
                    string ik = parseString();
                    expect(':');
                    if(ik == "type") it.id = parseString();
                    else if(ik == "w") it.w = (int)parseInt();
                    else if(ik == "h") it.h = (int)parseInt();
                    else if(ik == "v") it.v = parseInt();
                    else if(ik == "limit") it.limit = (int)parseInt();
                    else skipValue(skipValue);
                    if(peek() == ',') get();
                }
                get();
                in.items.push_back(it);
                if(peek() == ',') get();
            }
            get();
        } else {
            skipValue(skipValue);
        }
        if(peek() == ',') get();
    }
    return in;
}

// ==============================================================================================
// SOLVER LOGIC (Guillotine Packer)
// ==============================================================================================

Solution solve_guillotine(const Input& in, const vector<ItemInst>& items, int split_heuristic, int rect_heuristic) {
    Solution sol;
    vector<Rect> free_rects;
    free_rects.push_back({0, 0, in.bin.W, in.bin.H});

    // Heuristics:
    // split_heuristic: 0=SAS (Shorter Axis Split), 1=LAS (Longer Axis Split)
    // rect_heuristic: 0=BAF (Best Area Fit), 1=BSSF (Best Short Side Fit)

    for (const auto& item : items) {
        int best_rect_idx = -1;
        int best_rot = -1;
        long long best_score = -2e18; // We will maximize this score

        vector<int> rots;
        rots.push_back(0);
        if (in.bin.allow_rotate && item.w != item.h) rots.push_back(1);

        for (int r = 0; r < (int)free_rects.size(); ++r) {
            const Rect& fr = free_rects[r];
            for (int rot : rots) {
                int iw = (rot == 0) ? item.w : item.h;
                int ih = (rot == 0) ? item.h : item.w;
                if (iw <= fr.w && ih <= fr.h) {
                    long long score;
                    if (rect_heuristic == 0) { 
                        // BAF: Best Area Fit implies minimizing the free rect area.
                        // Score = -Area. Maximize score => minimize area.
                        score = -((long long)fr.w * fr.h);
                    } else { 
                        // BSSF: Minimize leftover on short axis
                        int rem_w = fr.w - iw;
                        int rem_h = fr.h - ih;
                        score = -min(rem_w, rem_h);
                    }

                    if (best_rect_idx == -1 || score > best_score) {
                        best_score = score;
                        best_rect_idx = r;
                        best_rot = rot;
                    }
                }
            }
        }

        if (best_rect_idx != -1) {
            Rect fr = free_rects[best_rect_idx];
            // Remove used rect (swap with back to be O(1))
            if (best_rect_idx < (int)free_rects.size() - 1)
                free_rects[best_rect_idx] = free_rects.back();
            free_rects.pop_back();

            int iw = (best_rot == 0) ? item.w : item.h;
            int ih = (best_rot == 0) ? item.h : item.w;

            sol.placements.push_back({item.id, fr.x, fr.y, best_rot});
            sol.total_profit += item.v;

            Rect right, top;
            bool split_horz = false; 
            
            // Split Heuristics
            if (split_heuristic == 0) { // SAS: Split along shorter axis
                split_horz = (fr.w < fr.h);
            } else { // LAS: Split along longer axis
                split_horz = (fr.w > fr.h);
            }

            if (split_horz) {
                // Horizontal cut: Top rect spans full width
                // Top: above item, width=fr.w
                // Right: right of item, height=ih
                top = {fr.x, fr.y + ih, fr.w, fr.h - ih};
                right = {fr.x + iw, fr.y, fr.w - iw, ih};
            } else {
                // Vertical cut: Right rect spans full height
                // Right: right of item, height=fr.h
                // Top: above item, width=iw
                top = {fr.x, fr.y + ih, iw, fr.h - ih};
                right = {fr.x + iw, fr.y, fr.w - iw, fr.h};
            }

            if (top.w > 0 && top.h > 0) free_rects.push_back(top);
            if (right.w > 0 && right.h > 0) free_rects.push_back(right);
        }
    }
    return sol;
}

// ==============================================================================================
// MAIN
// ==============================================================================================

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Read full input from stdin
    string buf; 
    {
        string line;
        while (getline(cin, line)) {
            buf += line;
            buf += '\n';
        }
    }

    if (buf.empty()) return 0;

    Input in = parseInput(buf);

    // Expand items into individual instances
    vector<ItemInst> all_items;
    all_items.reserve(25000);
    for (int i = 0; i < (int)in.items.size(); ++i) {
        for (int k = 0; k < in.items[i].limit; ++k) {
            all_items.push_back({i, in.items[i].w, in.items[i].h, in.items[i].v, in.items[i].id});
        }
    }

    auto start_time = chrono::high_resolution_clock::now();
    double time_limit = 0.95; // seconds

    Solution best_sol;
    best_sol.total_profit = -1;

    // Precompute sort orders
    vector<vector<ItemInst>> orders;
    
    // 1. Density descending
    vector<ItemInst> by_density = all_items;
    sort(by_density.begin(), by_density.end(), [](const ItemInst& a, const ItemInst& b){
        double da = (double)a.v / (a.w * a.h);
        double db = (double)b.v / (b.w * b.h);
        if (abs(da - db) > 1e-9) return da > db;
        if (a.v != b.v) return a.v > b.v;
        return (long long)a.w*a.h > (long long)b.w*b.h;
    });
    orders.push_back(by_density);

    // 2. Area descending
    vector<ItemInst> by_area = all_items;
    sort(by_area.begin(), by_area.end(), [](const ItemInst& a, const ItemInst& b){
        long long aa = (long long)a.w * a.h;
        long long ab = (long long)b.w * b.h;
        if (aa != ab) return aa > ab;
        return a.v > b.v;
    });
    orders.push_back(by_area);

    // 3. Value descending
    vector<ItemInst> by_value = all_items;
    sort(by_value.begin(), by_value.end(), [](const ItemInst& a, const ItemInst& b){
        if (a.v != b.v) return a.v > b.v;
        return (long long)a.w*a.h < (long long)b.w*b.h;
    });
    orders.push_back(by_value);
    
    // 4. Max Side descending
    vector<ItemInst> by_side = all_items;
    sort(by_side.begin(), by_side.end(), [](const ItemInst& a, const ItemInst& b){
        return max(a.w, a.h) > max(b.w, b.h);
    });
    orders.push_back(by_side);

    // Define search configurations
    struct Config { int ord; int split; int rect; };
    vector<Config> configs;
    configs.push_back({0, 0, 0}); // Density, SAS, BAF
    configs.push_back({0, 1, 0}); // Density, LAS, BAF
    configs.push_back({0, 0, 1}); // Density, SAS, BSSF
    configs.push_back({0, 1, 1}); // Density, LAS, BSSF
    configs.push_back({1, 0, 0}); // Area...
    configs.push_back({2, 0, 0}); // Value...
    configs.push_back({3, 0, 0}); // Side...
    
    int config_idx = 0;
    int seed = 123456789;
    vector<ItemInst> perturbed; 

    // Main optimization loop
    while (true) {
        auto now = chrono::high_resolution_clock::now();
        chrono::duration<double> diff = now - start_time;
        if (diff.count() > time_limit) break;

        vector<ItemInst>* current_items;
        int s_h, r_h;

        if (config_idx < (int)configs.size()) {
            current_items = &orders[configs[config_idx].ord];
            s_h = configs[config_idx].split;
            r_h = configs[config_idx].rect;
            config_idx++;
        } else {
            // Randomized search phase: perturb density order
            perturbed = orders[0];
            int n = perturbed.size();
            if (n > 0) {
                // Shuffle logic
                for (int k = 0; k < min(n, 200); ++k) {
                    seed = (seed * 1103515245 + 12345) & 0x7fffffff;
                    int i = k;
                    int j = k + (seed % (n - k));
                    swap(perturbed[i], perturbed[j]);
                }
                // Random pairs
                for(int k=0; k<50; ++k) {
                    seed = (seed * 1103515245 + 12345) & 0x7fffffff;
                    int i = seed % n;
                    seed = (seed * 1103515245 + 12345) & 0x7fffffff;
                    int j = seed % n;
                    swap(perturbed[i], perturbed[j]);
                }
            }
            current_items = &perturbed;
            seed = (seed * 1103515245 + 12345) & 0x7fffffff;
            s_h = seed % 2;
            seed = (seed * 1103515245 + 12345) & 0x7fffffff;
            r_h = seed % 2;
        }

        Solution s = solve_guillotine(in, *current_items, s_h, r_h);
        if (s.total_profit > best_sol.total_profit) {
            best_sol = s;
        }
    }

    // Output formatting
    cout << "{\"placements\":[";
    for (size_t i = 0; i < best_sol.placements.size(); ++i) {
        const auto& p = best_sol.placements[i];
        cout << "{\"type\":\"" << p.type_id << "\",\"x\":" << p.x 
             << ",\"y\":" << p.y << ",\"rot\":" << p.rot << "}";
        if (i < best_sol.placements.size() - 1) cout << ",";
    }
    cout << "]}" << endl;

    return 0;
}
#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <climits>

using namespace std;

// Structure for Item Types
struct ItemType {
    string id;
    int w, h, v, limit;
};

// Structure for a finalized placement
struct Placement {
    int type_idx; // Index into the global item_types vector
    int x, y, rot;
};

// Rectangle used for Free Space management
struct Rect {
    int x, y, w, h;
    // Check if this rectangle fully contains 'other'
    bool contains(const Rect& other) const {
        return other.x >= x && other.y >= y &&
               other.x + other.w <= x + w &&
               other.y + other.h <= y + h;
    }
};

// Global Problem Variables
int BIN_W, BIN_H;
bool ALLOW_ROTATE;
vector<ItemType> item_types;

// Manual JSON Parser
// This parser assumes the input strictly follows the problem statement structure.
void parse_input() {
    string json = "";
    string line;
    while (getline(cin, line)) json += line;

    // Helper to extract integer value for a key in a given range
    auto get_int = [&](string key, size_t start, size_t end) -> int {
        size_t key_pos = json.find("\"" + key + "\"", start);
        if (key_pos == string::npos || key_pos > end) return 0; 
        size_t colon = json.find(":", key_pos);
        size_t comma = json.find_first_of(",}", colon);
        string val = json.substr(colon + 1, comma - colon - 1);
        return stoi(val);
    };

    // Helper to extract boolean value
    auto get_bool = [&](string key, size_t start, size_t end) -> bool {
        size_t key_pos = json.find("\"" + key + "\"", start);
        if (key_pos == string::npos || key_pos > end) return false;
        size_t colon = json.find(":", key_pos);
        size_t comma = json.find_first_of(",}", colon);
        string val = json.substr(colon + 1, comma - colon - 1);
        if (val.find("true") != string::npos) return true;
        return false;
    };
    
    // Parse Bin
    size_t bin_pos = json.find("\"bin\"");
    size_t bin_start = json.find("{", bin_pos);
    size_t bin_end = json.find("}", bin_start);
    BIN_W = get_int("W", bin_start, bin_end);
    BIN_H = get_int("H", bin_start, bin_end);
    ALLOW_ROTATE = get_bool("allow_rotate", bin_start, bin_end);

    // Parse Items
    size_t items_pos = json.find("\"items\"");
    size_t items_arr_start = json.find("[", items_pos);
    size_t current = items_arr_start + 1;
    
    while (true) {
        size_t item_start = json.find("{", current);
        if (item_start == string::npos) break;
        size_t item_end = json.find("}", item_start);
        
        ItemType t;
        // Parse type ID manually to handle quotes
        size_t type_key = json.find("\"type\"", item_start);
        size_t colon = json.find(":", type_key);
        size_t q1 = json.find("\"", colon);
        size_t q2 = json.find("\"", q1 + 1);
        t.id = json.substr(q1 + 1, q2 - q1 - 1);
        
        t.w = get_int("w", item_start, item_end);
        t.h = get_int("h", item_start, item_end);
        t.v = get_int("v", item_start, item_end);
        t.limit = get_int("limit", item_start, item_end);
        
        item_types.push_back(t);
        current = item_end + 1;
    }
}

// Packer class implementing the Maximal Rectangles Heuristic
struct Packer {
    vector<Rect> free_rects;
    vector<Placement> placements;
    long long total_profit = 0;

    void init(int W, int H) {
        free_rects.clear();
        placements.clear();
        // Initial free space is the whole bin
        free_rects.push_back({0, 0, W, H});
        total_profit = 0;
    }

    // Try to place one instance of item type t_idx
    // Uses Best Short Side Fit (BSSF) heuristic
    bool place_item(int t_idx) {
        const auto& item = item_types[t_idx];
        int best_rect_idx = -1;
        int best_rot = 0;
        long long best_score_1 = -1; // Minimize short side residue
        long long best_score_2 = -1; // Minimize area residue

        for (int i = 0; i < free_rects.size(); ++i) {
            const auto& fr = free_rects[i];
            
            // Attempt normal orientation (rot = 0)
            if (item.w <= fr.w && item.h <= fr.h) {
                int leftover_w = fr.w - item.w;
                int leftover_h = fr.h - item.h;
                int short_side = min(leftover_w, leftover_h);
                long long area_rem = (long long)fr.w * fr.h - (long long)item.w * item.h;
                
                if (best_rect_idx == -1 || short_side < best_score_1 || 
                   (short_side == best_score_1 && area_rem < best_score_2)) {
                    best_score_1 = short_side;
                    best_score_2 = area_rem;
                    best_rect_idx = i;
                    best_rot = 0;
                }
            }
            
            // Attempt rotated orientation (rot = 1)
            if (ALLOW_ROTATE) {
                if (item.h <= fr.w && item.w <= fr.h) {
                    int leftover_w = fr.w - item.h;
                    int leftover_h = fr.h - item.w;
                    int short_side = min(leftover_w, leftover_h);
                    long long area_rem = (long long)fr.w * fr.h - (long long)item.h * item.w;
                    
                    if (best_rect_idx == -1 || short_side < best_score_1 || 
                       (short_side == best_score_1 && area_rem < best_score_2)) {
                        best_score_1 = short_side;
                        best_score_2 = area_rem;
                        best_rect_idx = i;
                        best_rot = 1;
                    }
                }
            }
        }

        if (best_rect_idx != -1) {
            Rect fr = free_rects[best_rect_idx];
            int w_place = (best_rot == 0) ? item.w : item.h;
            int h_place = (best_rot == 0) ? item.h : item.w;
            
            Placement p = {t_idx, fr.x, fr.y, best_rot};
            placements.push_back(p);
            total_profit += item.v;

            // Remove placed area from free rectangles and split
            update_free_rects({p.x, p.y, w_place, h_place});
            return true;
        }
        return false;
    }

    // Update free rectangles by subtracting the placed rectangle
    void update_free_rects(const Rect& placed) {
        vector<Rect> next_free;
        next_free.reserve(free_rects.size() * 2);
        
        for (const auto& fr : free_rects) {
            // Check intersection
            if (placed.x >= fr.x + fr.w || placed.x + placed.w <= fr.x ||
                placed.y >= fr.y + fr.h || placed.y + placed.h <= fr.y) {
                // No intersection
                next_free.push_back(fr);
            } else {
                // Split into max 4 rectangles
                if (placed.y + placed.h < fr.y + fr.h) 
                    next_free.push_back({fr.x, placed.y + placed.h, fr.w, fr.y + fr.h - (placed.y + placed.h)});
                if (placed.y > fr.y) 
                    next_free.push_back({fr.x, fr.y, fr.w, placed.y - fr.y});
                if (placed.x > fr.x) 
                    next_free.push_back({fr.x, fr.y, placed.x - fr.x, fr.h});
                if (placed.x + placed.w < fr.x + fr.w) 
                    next_free.push_back({placed.x + placed.w, fr.y, fr.x + fr.w - (placed.x + placed.w), fr.h});
            }
        }
        
        // Prune contained rectangles to keep the list size small (Maximal Rectangles property)
        free_rects.clear();
        for (size_t i = 0; i < next_free.size(); ++i) {
            bool contained = false;
            for (size_t j = 0; j < next_free.size(); ++j) {
                if (i != j && next_free[j].contains(next_free[i])) {
                    contained = true;
                    break;
                }
            }
            if (!contained) free_rects.push_back(next_free[i]);
        }
    }
};

long long best_profit = -1;
vector<Placement> best_placements;

// Solve for a specific permutation/priority order of item types
void solve(const vector<int>& order) {
    Packer p;
    p.init(BIN_W, BIN_H);
    vector<int> lims(item_types.size());
    for(int i=0; i<item_types.size(); ++i) lims[i] = item_types[i].limit;
    
    bool placed = true;
    while(placed) {
        placed = false;
        // Iterate through item types in priority order
        for(int idx : order) {
            if(lims[idx] > 0 && p.place_item(idx)) {
                lims[idx]--;
                placed = true;
                // Restart from the highest priority item to ensure greedy optimality for value
                break; 
            }
        }
    }
    
    if(p.total_profit > best_profit) {
        best_profit = p.total_profit;
        best_placements = p.placements;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    parse_input();
    
    // Base indices for sorting
    vector<int> idx(item_types.size());
    for(int i=0; i<idx.size(); ++i) idx[i] = i;
    
    // Heuristic 1: Sort by Value Density (Profit / Area) Descending
    vector<int> o1 = idx;
    sort(o1.begin(), o1.end(), [](int a, int b){
        double d1 = (double)item_types[a].v / (item_types[a].w * item_types[a].h);
        double d2 = (double)item_types[b].v / (item_types[b].w * item_types[b].h);
        return d1 > d2;
    });
    solve(o1);
    
    // Heuristic 2: Sort by Absolute Profit Descending
    vector<int> o2 = idx;
    sort(o2.begin(), o2.end(), [](int a, int b){
        return item_types[a].v > item_types[b].v;
    });
    solve(o2);
    
    // Heuristic 3: Sort by Area Descending
    vector<int> o3 = idx;
    sort(o3.begin(), o3.end(), [](int a, int b){
        return (long long)item_types[a].w * item_types[a].h > (long long)item_types[b].w * item_types[b].h;
    });
    solve(o3);
    
    // Heuristic 4: Sort by Max Dimension Descending
    vector<int> o4 = idx;
    sort(o4.begin(), o4.end(), [](int a, int b){
        return max(item_types[a].w, item_types[a].h) > max(item_types[b].w, item_types[b].h);
    });
    solve(o4);

    // Output JSON
    cout << "{\"placements\":[";
    for(size_t i=0; i<best_placements.size(); ++i) {
        const auto& p = best_placements[i];
        cout << "{\"type\":\"" << item_types[p.type_idx].id << "\",\"x\":" << p.x 
             << ",\"y\":" << p.y << ",\"rot\":" << p.rot << "}";
        if(i < best_placements.size()-1) cout << ",";
    }
    cout << "]}" << endl;

    return 0;
}
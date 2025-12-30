#include <iostream>
#include <string>
#include <vector>
#include <deque>
#include <algorithm>
#include <random>
#include <cctype>
#include <sstream>
#include <cmath>

using namespace std;

struct Item {
    string type;
    int w, h, v, limit;
};

struct PlacementOut {
    string type;
    int x, y, rot;
};

// Helper to extract integer value from a compact JSON string after a given key
int get_int(const string& str, const string& key) {
    size_t pos = str.find(key);
    if (pos == string::npos) return -1;
    pos += key.length();
    size_t end = str.find_first_of(",}", pos);
    string num = str.substr(pos, end - pos);
    return stoi(num);
}

int main() {
    // Read entire input
    string s;
    char ch;
    while (cin.get(ch)) s += ch;

    // Remove all whitespace
    s.erase(remove_if(s.begin(), s.end(), [](unsigned char c) { return isspace(c); }), s.end());

    // Parse bin
    size_t bin_start = s.find("\"bin\":{");
    if (bin_start == string::npos) return 0;
    bin_start += 6; // after "\"bin\":"
    size_t bin_end = s.find('}', bin_start);
    string bin_str = s.substr(bin_start, bin_end - bin_start + 1);

    int W = get_int(bin_str, "\"W\":");
    int H = get_int(bin_str, "\"H\":");
    bool allow_rotate = false;
    size_t rot_pos = bin_str.find("\"allow_rotate\":");
    if (rot_pos != string::npos) {
        rot_pos += 15; // length of "\"allow_rotate\":"
        if (bin_str.substr(rot_pos, 4) == "true")
            allow_rotate = true;
    }

    // Parse items array
    size_t items_start = s.find("\"items\":[");
    if (items_start == string::npos) return 0;
    items_start += 9; // after "\"items\":["
    size_t items_end = s.find(']', items_start);
    string items_str = s.substr(items_start, items_end - items_start);

    vector<Item> items;
    size_t pos = 0;
    while (pos < items_str.length()) {
        if (items_str[pos] == '{') {
            size_t end = items_str.find('}', pos);
            string item_str = items_str.substr(pos, end - pos + 1);
            Item it;
            // type
            size_t type_start = item_str.find("\"type\":\"");
            if (type_start == string::npos) { pos = end + 1; continue; }
            type_start += 8;
            size_t type_end = item_str.find('"', type_start);
            it.type = item_str.substr(type_start, type_end - type_start);
            // dimensions, profit, limit
            it.w = get_int(item_str, "\"w\":");
            it.h = get_int(item_str, "\"h\":");
            it.v = get_int(item_str, "\"v\":");
            it.limit = get_int(item_str, "\"limit\":");
            items.push_back(it);
            pos = end + 1;
        } else {
            pos++;
        }
    }

    int M = items.size();
    if (M == 0) {
        cout << "{\"placements\":[]}" << endl;
        return 0;
    }

    // Best solution found
    vector<PlacementOut> best_placements;
    long long best_profit = -1;

    // Different scoring types
    vector<int> score_types = {0, 1, 2, 3}; // 0: profit, 1: profit/area, 2: profit/width, 3: profit/height
    vector<long long> seeds = {12345, 67890, 13579, 24680, 97531};
    int num_seeds = 5;

    for (int st : score_types) {
        for (int seed_idx = 0; seed_idx < num_seeds; ++seed_idx) {
            long long seed = seeds[seed_idx] + st * 1000;
            mt19937 rng(seed);
            uniform_real_distribution<double> dist(0.0, 1e-6);

            vector<int> rem(M);
            for (int i = 0; i < M; ++i) rem[i] = items[i].limit;
            vector<int> height(W, 0);
            vector<PlacementOut> placements;
            long long profit = 0;

            while (true) {
                double best_score = -1;
                int best_x = -1, best_y = -1, best_i = -1, best_rot = -1;

                for (int i = 0; i < M; ++i) {
                    if (rem[i] == 0) continue;
                    for (int rot = 0; rot < 2; ++rot) {
                        if (rot == 1 && !allow_rotate) continue;
                        int w = (rot == 0 ? items[i].w : items[i].h);
                        int h = (rot == 0 ? items[i].h : items[i].w);
                        if (w > W || h > H) continue;
                        if (w == 0 || h == 0) continue;

                        // Sliding window maximum for width w
                        vector<int> M_array(W - w + 1);
                        deque<int> dq;
                        for (int j = 0; j < W; ++j) {
                            while (!dq.empty() && dq.front() <= j - w) dq.pop_front();
                            while (!dq.empty() && height[dq.back()] <= height[j]) dq.pop_back();
                            dq.push_back(j);
                            if (j >= w - 1) {
                                M_array[j - w + 1] = height[dq.front()];
                            }
                        }

                        // Find best position for this item/orientation
                        for (int x = 0; x <= W - w; ++x) {
                            int base_y = M_array[x];
                            if (base_y + h <= H) {
                                double score;
                                if (st == 0) score = items[i].v;
                                else if (st == 1) score = (double)items[i].v / (w * h);
                                else if (st == 2) score = (double)items[i].v / w;
                                else if (st == 3) score = (double)items[i].v / h;
                                // Random tie‑breaking
                                score += dist(rng);
                                if (score > best_score) {
                                    best_score = score;
                                    best_x = x;
                                    best_y = base_y;
                                    best_i = i;
                                    best_rot = rot;
                                }
                            }
                        }
                    }
                }

                if (best_score == -1) break; // No feasible placement left

                // Place the chosen item
                placements.push_back({items[best_i].type, best_x, best_y, best_rot});
                profit += items[best_i].v;
                rem[best_i]--;

                // Update height array
                int w_placed = (best_rot == 0 ? items[best_i].w : items[best_i].h);
                int h_placed = (best_rot == 0 ? items[best_i].h : items[best_i].w);
                for (int i = best_x; i < best_x + w_placed; ++i) {
                    height[i] = best_y + h_placed;
                }
            }

            if (profit > best_profit) {
                best_profit = profit;
                best_placements = placements;
            }
        }
    }

    // Output the best solution as JSON
    cout << "{\"placements\":[";
    for (size_t i = 0; i < best_placements.size(); ++i) {
        if (i > 0) cout << ",";
        cout << "{\"type\":\"" << best_placements[i].type << "\",";
        cout << "\"x\":" << best_placements[i].x << ",";
        cout << "\"y\":" << best_placements[i].y << ",";
        cout << "\"rot\":" << best_placements[i].rot << "}";
    }
    cout << "]}" << endl;

    return 0;
}
#include <iostream>
#include <vector>
#include <string>
#include <deque>
#include <unordered_map>
#include <unordered_set>
#include <functional>
#include <algorithm>
#include <cctype>
#include <cmath>

using namespace std;

struct Placement {
    string type;
    int x, y, rot;
};

struct Item {
    string type;
    int w, h, v, limit;
    int remaining;
};

struct Candidate {
    int idx;        // index in items vector
    int rot;        // 0 or 1
    int w, h;       // dimensions after rotation (if applied)
    double score;   // computed by scoring function
};

void skip_whitespace(const string& s, size_t& pos) {
    while (pos < s.size() && (s[pos] == ' ' || s[pos] == '\n' || s[pos] == '\t' || s[pos] == '\r'))
        pos++;
}

string parse_string(const string& s, size_t& pos) {
    // expects opening double quote
    if (s[pos] != '"') return "";
    pos++;
    size_t start = pos;
    while (pos < s.size() && s[pos] != '"') pos++;
    string result = s.substr(start, pos - start);
    pos++; // skip closing quote
    return result;
}

int parse_int(const string& s, size_t& pos) {
    int sign = 1;
    if (s[pos] == '-') {
        sign = -1;
        pos++;
    }
    int val = 0;
    while (pos < s.size() && isdigit(s[pos])) {
        val = val * 10 + (s[pos] - '0');
        pos++;
    }
    return sign * val;
}

bool parse_bool(const string& s, size_t& pos) {
    if (s.substr(pos, 4) == "true") {
        pos += 4;
        return true;
    }
    if (s.substr(pos, 5) == "false") {
        pos += 5;
        return false;
    }
    return false;
}

void parse_input(const string& json_str, int& W, int& H, bool& allow_rotate, vector<Item>& items) {
    size_t pos = 0;
    skip_whitespace(json_str, pos);
    if (json_str[pos] != '{') return;
    pos++;

    // Parse two keys: "bin" and "items"
    while (pos < json_str.size()) {
        skip_whitespace(json_str, pos);
        if (json_str[pos] == '}') break;
        string key = parse_string(json_str, pos);
        skip_whitespace(json_str, pos);
        if (json_str[pos] != ':') return;
        pos++;
        skip_whitespace(json_str, pos);

        if (key == "bin") {
            // parse bin object
            if (json_str[pos] != '{') return;
            pos++;
            while (pos < json_str.size()) {
                skip_whitespace(json_str, pos);
                if (json_str[pos] == '}') break;
                string bin_key = parse_string(json_str, pos);
                skip_whitespace(json_str, pos);
                if (json_str[pos] != ':') return;
                pos++;
                skip_whitespace(json_str, pos);
                if (bin_key == "W") {
                    W = parse_int(json_str, pos);
                } else if (bin_key == "H") {
                    H = parse_int(json_str, pos);
                } else if (bin_key == "allow_rotate") {
                    allow_rotate = parse_bool(json_str, pos);
                } else {
                    // unknown key, skip
                    while (pos < json_str.size() && json_str[pos] != ',' && json_str[pos] != '}') pos++;
                }
                skip_whitespace(json_str, pos);
                if (json_str[pos] == ',') {
                    pos++;
                    continue;
                }
            }
            if (json_str[pos] != '}') return;
            pos++;
        } else if (key == "items") {
            // parse items array
            if (json_str[pos] != '[') return;
            pos++;
            while (pos < json_str.size()) {
                skip_whitespace(json_str, pos);
                if (json_str[pos] == ']') break;
                if (json_str[pos] != '{') return;
                pos++;
                Item it;
                while (pos < json_str.size()) {
                    skip_whitespace(json_str, pos);
                    if (json_str[pos] == '}') break;
                    string item_key = parse_string(json_str, pos);
                    skip_whitespace(json_str, pos);
                    if (json_str[pos] != ':') return;
                    pos++;
                    skip_whitespace(json_str, pos);
                    if (item_key == "type") {
                        it.type = parse_string(json_str, pos);
                    } else if (item_key == "w") {
                        it.w = parse_int(json_str, pos);
                    } else if (item_key == "h") {
                        it.h = parse_int(json_str, pos);
                    } else if (item_key == "v") {
                        it.v = parse_int(json_str, pos);
                    } else if (item_key == "limit") {
                        it.limit = parse_int(json_str, pos);
                    } else {
                        // unknown key, skip
                        while (pos < json_str.size() && json_str[pos] != ',' && json_str[pos] != '}') pos++;
                    }
                    skip_whitespace(json_str, pos);
                    if (json_str[pos] == ',') {
                        pos++;
                        continue;
                    }
                }
                if (json_str[pos] != '}') return;
                pos++;
                it.remaining = it.limit;
                items.push_back(it);
                skip_whitespace(json_str, pos);
                if (json_str[pos] == ',') {
                    pos++;
                    continue;
                }
            }
            if (json_str[pos] != ']') return;
            pos++;
        } else {
            // unknown top-level key, skip
            while (pos < json_str.size() && json_str[pos] != ',' && json_str[pos] != '}') pos++;
        }
        skip_whitespace(json_str, pos);
        if (json_str[pos] == ',') {
            pos++;
            continue;
        }
    }
}

// Sliding window maximum (deque method)
vector<int> compute_max_height(const vector<int>& height, int w) {
    int n = height.size();
    vector<int> maxH(n - w + 1);
    deque<int> dq;
    for (int i = 0; i < n; ++i) {
        while (!dq.empty() && dq.front() <= i - w) dq.pop_front();
        while (!dq.empty() && height[dq.back()] <= height[i]) dq.pop_back();
        dq.push_back(i);
        if (i >= w - 1) {
            maxH[i - w + 1] = height[dq.front()];
        }
    }
    return maxH;
}

struct Result {
    long long profit;
    vector<Placement> placements;
};

Result solve(const vector<Item>& original_items, int W, int H, bool allow_rotate,
             function<double(int v, int w, int h)> scoring) {
    vector<Item> items = original_items; // copy to modify remaining counts
    vector<int> height(W, 0);
    vector<Placement> placements;
    long long total_profit = 0;

    while (true) {
        // Collect candidate rectangles (item index, rotation, dimensions, score)
        vector<Candidate> candidates;
        unordered_set<int> distinct_widths;
        for (size_t i = 0; i < items.size(); ++i) {
            if (items[i].remaining == 0) continue;
            // orientation 0 (no rotation)
            int w0 = items[i].w, h0 = items[i].h;
            if (w0 <= W && h0 <= H) {
                candidates.push_back({(int)i, 0, w0, h0, scoring(items[i].v, w0, h0)});
                distinct_widths.insert(w0);
            }
            // orientation 1 (rotated) if allowed
            if (allow_rotate) {
                int w1 = items[i].h, h1 = items[i].w;
                if (w1 <= W && h1 <= H) {
                    candidates.push_back({(int)i, 1, w1, h1, scoring(items[i].v, w1, h1)});
                    distinct_widths.insert(w1);
                }
            }
        }
        if (candidates.empty()) break;

        // Precompute max-height arrays for each distinct width
        unordered_map<int, vector<int>> maxH_map;
        for (int w : distinct_widths) {
            maxH_map[w] = compute_max_height(height, w);
        }

        // Evaluate each candidate
        double best_score = -1.0;
        int best_cand = -1;
        int best_x = -1, best_y = -1;

        for (size_t c = 0; c < candidates.size(); ++c) {
            const Candidate& cand = candidates[c];
            const vector<int>& maxH = maxH_map.at(cand.w);
            int cand_best_y = H + 1;
            int cand_best_x = -1;
            for (int x = 0; x <= W - cand.w; ++x) {
                int y = maxH[x];
                if (y + cand.h <= H) {
                    if (y < cand_best_y) {
                        cand_best_y = y;
                        cand_best_x = x;
                    } else if (y == cand_best_y && x < cand_best_x) {
                        cand_best_x = x;
                    }
                }
            }
            if (cand_best_x != -1) {
                if (cand.score > best_score) {
                    best_score = cand.score;
                    best_cand = c;
                    best_x = cand_best_x;
                    best_y = cand_best_y;
                }
            }
        }

        if (best_cand == -1) break; // no feasible placement

        // Perform the placement
        const Candidate& cand = candidates[best_cand];
        Item& it = items[cand.idx];
        int new_height = best_y + cand.h;
        for (int x = best_x; x < best_x + cand.w; ++x) {
            height[x] = new_height;
        }
        it.remaining--;
        total_profit += it.v;
        placements.push_back({it.type, best_x, best_y, cand.rot});
    }

    return {total_profit, placements};
}

int main() {
    // Read entire input
    string input;
    cin.seekg(0, ios::end);
    input.reserve(cin.tellg());
    cin.seekg(0, ios::beg);
    input.assign((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());

    int W, H;
    bool allow_rotate;
    vector<Item> items;
    parse_input(input, W, H, allow_rotate, items);

    // Define scoring functions to try
    vector<pair<string, function<double(int, int, int)>>> scorings = {
        {"value_density", [](int v, int w, int h) { return (double)v / (w * h); }},
        {"profit",        [](int v, int w, int h) { return (double)v; }},
        {"area_inverse",  [](int v, int w, int h) { return 1.0 / (w * h); }}, // prefers small items
    };

    Result best_result;
    best_result.profit = -1;

    for (auto& scoring : scorings) {
        Result res = solve(items, W, H, allow_rotate, scoring.second);
        if (res.profit > best_result.profit) {
            best_result = move(res);
        }
    }

    // Output best packing found
    cout << "{\"placements\":[";
    for (size_t i = 0; i < best_result.placements.size(); ++i) {
        if (i > 0) cout << ",";
        const Placement& p = best_result.placements[i];
        cout << "{\"type\":\"" << p.type << "\",\"x\":" << p.x << ",\"y\":" << p.y << ",\"rot\":" << p.rot << "}";
    }
    cout << "]}" << endl;

    return 0;
}
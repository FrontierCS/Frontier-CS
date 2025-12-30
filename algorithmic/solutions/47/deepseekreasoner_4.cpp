#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>
#include <random>
#include <utility>
#include <tuple>
#include <cassert>
#include <cstring>

using namespace std;

// ------------------------------------------------------------
// Simple JSON parsing (for the given fixed structure)
// ------------------------------------------------------------
struct Bin {
    int W, H;
    bool allow_rotate;
};

struct ItemType {
    string type;
    int w, h, v, limit;
    double value_density;
    int area;
};

bool parse_input(Bin& bin, vector<ItemType>& items) {
    string input;
    char ch;
    while (cin.get(ch)) input += ch;

    // Very basic parsing, assuming well-formed JSON.
    // Find "bin": {...}
    size_t pos = input.find("\"bin\"");
    if (pos == string::npos) return false;
    pos = input.find('{', pos);
    size_t end_pos = input.find('}', pos);
    string bin_str = input.substr(pos, end_pos - pos + 1);

    // Extract W, H, allow_rotate
    pos = bin_str.find("\"W\"");
    if (pos == string::npos) return false;
    pos = bin_str.find(':', pos);
    bin.W = stoi(bin_str.substr(pos + 1));

    pos = bin_str.find("\"H\"");
    if (pos == string::npos) return false;
    pos = bin_str.find(':', pos);
    bin.H = stoi(bin_str.substr(pos + 1));

    pos = bin_str.find("\"allow_rotate\"");
    if (pos == string::npos) return false;
    pos = bin_str.find(':', pos);
    size_t comma = bin_str.find(',', pos);
    if (comma == string::npos) comma = bin_str.find('}', pos);
    string bool_str = bin_str.substr(pos + 1, comma - pos - 1);
    if (bool_str.find("true") != string::npos) bin.allow_rotate = true;
    else bin.allow_rotate = false;

    // Find "items": [...]
    pos = input.find("\"items\"");
    if (pos == string::npos) return false;
    pos = input.find('[', pos);
    end_pos = input.find(']', pos);
    string items_str = input.substr(pos, end_pos - pos + 1);

    // Parse each item object
    size_t start = 0;
    while ((start = items_str.find('{', start)) != string::npos) {
        size_t item_end = items_str.find('}', start);
        string item_obj = items_str.substr(start, item_end - start + 1);
        ItemType it;

        size_t p = item_obj.find("\"type\"");
        if (p == string::npos) return false;
        p = item_obj.find(':', p);
        size_t quote1 = item_obj.find('\"', p);
        size_t quote2 = item_obj.find('\"', quote1 + 1);
        it.type = item_obj.substr(quote1 + 1, quote2 - quote1 - 1);

        p = item_obj.find("\"w\"");
        if (p == string::npos) return false;
        p = item_obj.find(':', p);
        it.w = stoi(item_obj.substr(p + 1));

        p = item_obj.find("\"h\"");
        if (p == string::npos) return false;
        p = item_obj.find(':', p);
        it.h = stoi(item_obj.substr(p + 1));

        p = item_obj.find("\"v\"");
        if (p == string::npos) return false;
        p = item_obj.find(':', p);
        it.v = stoi(item_obj.substr(p + 1));

        p = item_obj.find("\"limit\"");
        if (p == string::npos) return false;
        p = item_obj.find(':', p);
        it.limit = stoi(item_obj.substr(p + 1));

        it.area = it.w * it.h;
        it.value_density = double(it.v) / it.area;

        items.push_back(it);
        start = item_end + 1;
    }
    return true;
}

// ------------------------------------------------------------
// Skyline packing
// ------------------------------------------------------------
class Skyline {
public:
    int W, H;
    vector<pair<int, int>> pts; // (x, height) from x to next x

    Skyline(int width, int height) : W(width), H(height) {
        pts.emplace_back(0, 0);
        pts.emplace_back(width, 0); // sentinel
    }

    // Find the lowest leftmost position for a rectangle of size w x h.
    // Returns (found, x, y) where y is the base height.
    tuple<bool, int, int> find_position(int w, int h) {
        int best_x = -1, best_y = H + 1;
        for (size_t i = 0; i < pts.size() - 1; ++i) {
            int start_x = pts[i].first;
            if (start_x + w > W) continue;
            int needed = w;
            int max_h = 0;
            size_t j = i;
            while (needed > 0 && j < pts.size() - 1) {
                int seg_width = pts[j + 1].first - pts[j].first;
                int seg_height = pts[j].second;
                if (seg_width >= needed) {
                    max_h = max(max_h, seg_height);
                    needed = 0;
                    break;
                } else {
                    max_h = max(max_h, seg_height);
                    needed -= seg_width;
                    ++j;
                }
            }
            if (needed == 0) {
                int y = max_h;
                if (y + h <= H) {
                    if (y < best_y || (y == best_y && start_x < best_x)) {
                        best_y = y;
                        best_x = start_x;
                    }
                }
            }
        }
        if (best_x == -1) return {false, 0, 0};
        return {true, best_x, best_y};
    }

    // Place a rectangle at (x0, y0) with size w x h, update skyline.
    void place_rectangle(int x0, int y0, int w, int h) {
        int x1 = x0 + w;
        int new_h = y0 + h;

        vector<pair<int, int>> new_pts;
        size_t i = 0;
        // points before x0
        while (i < pts.size() && pts[i].first < x0) {
            new_pts.push_back(pts[i]);
            ++i;
        }
        // ensure a point at x0
        if (new_pts.empty() || new_pts.back().first != x0) {
            new_pts.emplace_back(x0, new_h);
        } else {
            new_pts.back().second = new_h;
        }
        // skip points inside (x0, x1)
        while (i < pts.size() && pts[i].first <= x1) {
            ++i;
        }
        // point at x1 with original height
        int orig_h_x1 = 0;
        for (size_t j = 0; j + 1 < pts.size(); ++j) {
            if (pts[j].first <= x1 && x1 < pts[j + 1].first) {
                orig_h_x1 = pts[j].second;
                break;
            }
        }
        if (x1 != x0) {
            new_pts.emplace_back(x1, orig_h_x1);
        }
        // remaining points
        while (i < pts.size()) {
            new_pts.push_back(pts[i]);
            ++i;
        }
        // merge consecutive points with same height
        vector<pair<int, int>> merged;
        for (const auto& p : new_pts) {
            if (merged.empty() || merged.back().second != p.second || p.first == W) {
                merged.push_back(p);
            }
        }
        // ensure last point is W
        if (merged.back().first != W) {
            merged.emplace_back(W, 0);
        }
        pts = merged;
    }
};

// ------------------------------------------------------------
// Placement structure
// ------------------------------------------------------------
struct Placement {
    string type;
    int x, y;
    int rot;
};

// ------------------------------------------------------------
// Ordering strategies
// ------------------------------------------------------------
enum Ordering {
    BY_VALUE_DENSITY_DESC,
    BY_HEIGHT_DESC,
    BY_WIDTH_DESC,
    BY_AREA_DESC,
    BY_PROFIT_DESC,
    RANDOM_ORDER
};

struct ItemInst {
    string type;
    int w, h, v;
    int rot; // 0 or 1, but we will decide later
};

void sort_items(vector<ItemInst>& items, Ordering ord, mt19937& rng) {
    if (ord == RANDOM_ORDER) {
        shuffle(items.begin(), items.end(), rng);
        return;
    }
    auto cmp = [ord](const ItemInst& a, const ItemInst& b) -> bool {
        switch (ord) {
            case BY_VALUE_DENSITY_DESC: {
                double da = double(a.v) / (a.w * a.h);
                double db = double(b.v) / (b.w * b.h);
                if (fabs(da - db) > 1e-9) return da > db;
                break;
            }
            case BY_HEIGHT_DESC:
                if (a.h != b.h) return a.h > b.h;
                break;
            case BY_WIDTH_DESC:
                if (a.w != b.w) return a.w > b.w;
                break;
            case BY_AREA_DESC:
                if (a.w * a.h != b.w * b.h) return a.w * a.h > b.w * b.h;
                break;
            case BY_PROFIT_DESC:
                if (a.v != b.v) return a.v > b.v;
                break;
            default: break;
        }
        // tie-breakers
        if (a.w != b.w) return a.w > b.w;
        if (a.h != b.h) return a.h > b.h;
        return a.v > b.v;
    };
    sort(items.begin(), items.end(), cmp);
}

// ------------------------------------------------------------
// Main packing routine
// ------------------------------------------------------------
vector<Placement> pack(const Bin& bin, const vector<ItemType>& item_types, Ordering ord, int seed) {
    mt19937 rng(seed);
    Skyline sky(bin.W, bin.H);
    vector<Placement> placements;
    int total_profit = 0;

    // Build list of item instances to try
    vector<ItemInst> to_pack;
    long long bin_area = (long long)bin.W * bin.H;
    for (const auto& it : item_types) {
        // decide how many copies to attempt
        long long item_area = it.area;
        int max_by_area = (item_area == 0) ? it.limit : min(it.limit, (int)(bin_area / item_area * 3 + 2));
        int n_try = min(it.limit, max(50, max_by_area));
        n_try = min(n_try, 500); // safety cap
        for (int k = 0; k < n_try; ++k) {
            to_pack.push_back({it.type, it.w, it.h, it.v, 0});
        }
    }

    // Sort/shuffle according to ordering
    sort_items(to_pack, ord, rng);

    // Greedy packing
    for (const auto& inst : to_pack) {
        int w0 = inst.w, h0 = inst.h;
        int w1 = inst.h, h1 = inst.w; // rotated
        bool try0 = true;
        bool try1 = bin.allow_rotate && (w1 <= bin.W && h1 <= bin.H);
        int best_x = -1, best_y = -1, best_w = 0, best_h = 0, best_rot = 0;
        // try original orientation
        if (try0) {
            auto [found, x, y] = sky.find_position(w0, h0);
            if (found) {
                best_x = x; best_y = y; best_w = w0; best_h = h0; best_rot = 0;
            }
        }
        // try rotated orientation
        if (try1) {
            auto [found, x, y] = sky.find_position(w1, h1);
            if (found) {
                if (best_x == -1 || y < best_y || (y == best_y && (w1*h1 < best_w*best_h))) {
                    best_x = x; best_y = y; best_w = w1; best_h = h1; best_rot = 1;
                }
            }
        }
        if (best_x != -1) {
            sky.place_rectangle(best_x, best_y, best_w, best_h);
            placements.push_back({inst.type, best_x, best_y, best_rot});
            total_profit += inst.v;
        }
    }
    return placements;
}

// ------------------------------------------------------------
// Output JSON
// ------------------------------------------------------------
void output_placements(const vector<Placement>& placements) {
    cout << "{\"placements\":[";
    bool first = true;
    for (const auto& p : placements) {
        if (!first) cout << ",";
        first = false;
        cout << "{\"type\":\"" << p.type << "\",\"x\":" << p.x << ",\"y\":" << p.y << ",\"rot\":" << p.rot << "}";
    }
    cout << "]}\n";
}

// ------------------------------------------------------------
// Main
// ------------------------------------------------------------
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Bin bin;
    vector<ItemType> items;
    if (!parse_input(bin, items)) {
        // fallback: output empty placement
        cout << "{\"placements\":[]}\n";
        return 0;
    }

    vector<Placement> best_placements;
    int best_profit = -1;

    // Orderings to try
    vector<Ordering> orderings = {
        BY_VALUE_DENSITY_DESC,
        BY_HEIGHT_DESC,
        BY_WIDTH_DESC,
        BY_AREA_DESC,
        BY_PROFIT_DESC,
        RANDOM_ORDER,
        RANDOM_ORDER,
        RANDOM_ORDER,
        RANDOM_ORDER
    };

    // Try each ordering with a few different seeds
    int seed_base = 12345;
    for (size_t i = 0; i < orderings.size(); ++i) {
        int seed = seed_base + i * 1007;
        auto placements = pack(bin, items, orderings[i], seed);
        // compute profit
        int profit = 0;
        for (const auto& p : placements) {
            // find item type
            for (const auto& it : items) {
                if (it.type == p.type) {
                    profit += it.v;
                    break;
                }
            }
        }
        if (profit > best_profit) {
            best_profit = profit;
            best_placements = placements;
        }
    }

    output_placements(best_placements);
    return 0;
}
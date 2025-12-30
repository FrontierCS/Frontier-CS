#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <functional>
#include <numeric>
#include <vector>

// Using the nlohmann/json library for easy JSON parsing and serialization.
// This is a header-only library. In a competition setting, one might
// bundle it with the source or use provided libraries.
#include "json.hpp"

using json = nlohmann::json;

struct Bin {
    int W, H;
    bool allow_rotate;
};

struct ItemType {
    std::string type;
    int id;
    int w, h, v, limit;
};

struct Placement {
    int type_id;
    int x, y;
    bool rot;
};

struct PlacementResult {
    bool found;
    int x, y;
    int score1, score2;
};

// Finds the best position for an item of size (w, h) using a skyline data structure.
// The "best" position is determined by BL_mode:
// true (Bottom-Left): Minimizes y, then x.
// false (Left-Bottom): Minimizes x, then y.
PlacementResult find_best_place(const Bin& bin, const std::map<int, int>& skyline, int w, int h, bool BL_mode) {
    PlacementResult best_res = {false, -1, -1, 0, 0};

    if (BL_mode) {
        best_res.score1 = bin.H + 1; // min_y
        best_res.score2 = bin.W + 1; // min_x
    } else {
        best_res.score1 = bin.W + 1; // min_x
        best_res.score2 = bin.H + 1; // min_y
    }

    std::vector<int> candidate_x;
    for (auto const& [x_coord, y_coord] : skyline) {
        candidate_x.push_back(x_coord);
        if (x_coord >= w) {
            candidate_x.push_back(x_coord - w);
        }
    }
    std::sort(candidate_x.begin(), candidate_x.end());
    candidate_x.erase(std::unique(candidate_x.begin(), candidate_x.end()), candidate_x.end());

    for (int x : candidate_x) {
        if (x < 0 || x + w > bin.W) continue;

        auto it = skyline.upper_bound(x);
        if (it != skyline.begin()) --it;

        int base_y = 0;
        while (it != skyline.end() && it->first < x + w) {
            base_y = std::max(base_y, it->second);
            ++it;
        }

        if (base_y + h <= bin.H) {
            if (BL_mode) {
                if (base_y < best_res.score1 || (base_y == best_res.score1 && x < best_res.score2)) {
                    best_res = {true, x, base_y, base_y, x};
                }
            } else {
                if (x < best_res.score1 || (x == best_res.score1 && base_y < best_res.score2)) {
                    best_res = {true, x, base_y, x, base_y};
                }
            }
        }
    }
    return best_res;
}

// Updates the skyline after placing an item.
void update_skyline(std::map<int, int>& skyline, int x, int y, int w, int h) {
    int new_y = y + h;

    auto it_end = skyline.upper_bound(x + w);
    int last_y = std::prev(it_end)->second;

    auto it_start = skyline.upper_bound(x);
    skyline.erase(it_start, it_end);

    skyline[x] = new_y;
    auto it_x = skyline.find(x);
    if (it_x != skyline.begin() && std::prev(it_x)->second == new_y) {
        skyline.erase(it_x);
    }

    skyline[x + w] = last_y;
    auto it_xw = skyline.find(x + w);
    if (it_xw != skyline.begin() && std::prev(it_xw)->second == last_y) {
        skyline.erase(it_xw);
    }
}

struct SolverResult {
    long long profit;
    std::vector<Placement> placements;
};

// Main solver function. It takes an ordering of items and a placement heuristic,
// and returns the total profit and list of placements.
SolverResult solve(const Bin& bin, const std::vector<ItemType>& item_types, const std::vector<int>& item_order, bool BL_mode) {
    std::vector<int> limits(item_types.size());
    for (size_t i = 0; i < item_types.size(); ++i) {
        limits[i] = item_types[i].limit;
    }

    std::map<int, int> skyline;
    skyline[0] = 0;

    long long total_profit = 0;
    std::vector<Placement> placements;

    for (int type_idx : item_order) {
        const auto& item = item_types[type_idx];
        while (limits[type_idx] > 0) {
            PlacementResult res_orig = {false};
            if (item.w <= bin.W && item.h <= bin.H) {
                res_orig = find_best_place(bin, skyline, item.w, item.h, BL_mode);
            }

            PlacementResult res_rot = {false};
            if (bin.allow_rotate && item.w != item.h && item.h <= bin.W && item.w <= bin.H) {
                res_rot = find_best_place(bin, skyline, item.h, item.w, BL_mode);
            }

            bool place_orig = false;
            bool place_rot = false;

            if (res_orig.found && !res_rot.found) {
                place_orig = true;
            } else if (!res_orig.found && res_rot.found) {
                place_rot = true;
            } else if (res_orig.found && res_rot.found) {
                if (res_orig.score1 < res_rot.score1 || (res_orig.score1 == res_rot.score1 && res_orig.score2 <= res_rot.score2)) {
                    place_orig = true;
                } else {
                    place_rot = true;
                }
            }

            if (place_orig) {
                placements.push_back({type_idx, res_orig.x, res_orig.y, false});
                total_profit += item.v;
                limits[type_idx]--;
                update_skyline(skyline, res_orig.x, res_orig.y, item.w, item.h);
            } else if (place_rot) {
                placements.push_back({type_idx, res_rot.x, res_rot.y, true});
                total_profit += item.v;
                limits[type_idx]--;
                update_skyline(skyline, res_rot.x, res_rot.y, item.h, item.w);
            } else {
                break;
            }
        }
    }
    return {total_profit, placements};
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    json data;
    std::cin >> data;

    Bin bin;
    bin.W = data["bin"]["W"];
    bin.H = data["bin"]["H"];
    bin.allow_rotate = data["bin"]["allow_rotate"];

    std::vector<ItemType> item_types;
    int id_counter = 0;
    for (const auto& item_json : data["items"]) {
        item_types.push_back({
            item_json["type"],
            id_counter++,
            item_json["w"],
            item_json["h"],
            item_json["v"],
            item_json["limit"]
        });
    }

    std::vector<std::function<bool(const ItemType&, const ItemType&)>> sorters;
    sorters.push_back([](const ItemType& a, const ItemType& b) { return (double)a.v / (a.w * a.h) > (double)b.v / (b.w * b.h); });
    sorters.push_back([](const ItemType& a, const ItemType& b) { return a.h > b.h; });
    sorters.push_back([](const ItemType& a, const ItemType& b) { return a.w > b.w; });
    sorters.push_back([](const ItemType& a, const ItemType& b) { return a.w * a.h > b.w * b.h; });
    sorters.push_back([](const ItemType& a, const ItemType& b) { return std::max(a.w, a.h) > std::max(b.w, b.h); });
    sorters.push_back([](const ItemType& a, const ItemType& b) { return a.v > b.v; });
    sorters.push_back([](const ItemType& a, const ItemType& b) { return a.w * a.h < b.w * b.h; });
    sorters.push_back([](const ItemType& a, const ItemType& b) { return std::max(a.w, a.h) < std::max(b.w, b.h); });
    sorters.push_back([](const ItemType& a, const ItemType& b) { return std::min(a.w, a.h) > std::min(b.w, b.h); });
    sorters.push_back([](const ItemType& a, const ItemType& b) { return a.w + a.h > b.w + b.h; });
    sorters.push_back([](const ItemType& a, const ItemType& b) { return a.h < b.h; });
    sorters.push_back([](const ItemType& a, const ItemType& b) { return a.w < b.w; });


    SolverResult best_result = {0, {}};

    for (const auto& sorter : sorters) {
        std::vector<int> item_order(item_types.size());
        std::iota(item_order.begin(), item_order.end(), 0);
        std::sort(item_order.begin(), item_order.end(), [&](int a, int b) {
            return sorter(item_types[a], item_types[b]);
        });

        for (bool BL_mode : {true, false}) {
            SolverResult current_result = solve(bin, item_types, item_order, BL_mode);
            if (current_result.profit > best_result.profit) {
                best_result = current_result;
            }
        }
    }

    json output;
    output["placements"] = json::array();
    for (const auto& p : best_result.placements) {
        json placement_obj;
        placement_obj["type"] = item_types[p.type_id].type;
        placement_obj["x"] = p.x;
        placement_obj["y"] = p.y;
        placement_obj["rot"] = p.rot ? 1 : 0;
        output["placements"].push_back(placement_obj);
    }
    std::cout << output.dump() << std::endl;

    return 0;
}
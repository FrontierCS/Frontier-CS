#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <set>
#include <functional>
#include <numeric>

// Using the nlohmann/json library for JSON parsing and generation.
// It's a single-header library, often available in competitive programming platforms.
#include "json.hpp"

using json = nlohmann::json;

struct Bin {
    int W, H;
    bool allow_rotate;
};

struct ItemType {
    std::string id;
    int w, h, v, limit;
    int original_idx;
};

struct ItemVariant {
    int type_idx;
    int w, h, v;
    bool rot;
    
    // Precomputed values for sorting
    double density;
    long long area;
    int max_dim;
    int min_dim;
    int perimeter;
};

struct Placement {
    std::string id;
    int x, y;
    bool rot;
};

// Finds the best bottom-left position for a rectangle of size (w, h)
std::pair<int, int> find_best_pos(int w, int h, const std::map<int, int>& skyline, int W, int H) {
    int best_x = -1;
    int best_y = H + 1;

    std::set<int> candidates;
    candidates.insert(0);
    for (const auto& p : skyline) {
        candidates.insert(p.first);
        if (p.first >= w) {
            candidates.insert(p.first - w);
        }
    }
    
    for (int x : candidates) {
        if (x < 0 || x + w > W) {
            continue;
        }

        int y_base = 0;
        auto it = skyline.upper_bound(x);
        --it;
        
        while (true) {
            y_base = std::max(y_base, it->second);
            auto next_it = std::next(it);
            if (next_it == skyline.end() || next_it->first >= x + w) {
                break;
            }
            it = next_it;
        }

        if (y_base + h <= H) {
            if (y_base < best_y) {
                best_y = y_base;
                best_x = x;
            }
        }
    }

    if (best_x == -1) {
        return {-1, -1};
    }
    return {best_x, best_y};
}

// Updates the skyline after placing a rectangle
void update_skyline(std::map<int, int>& skyline, int x, int y, int w, int h) {
    int new_y = y + h;

    auto it_after = skyline.upper_bound(x + w);
    int h_after = std::prev(it_after)->second;

    auto start_it = skyline.upper_bound(x);
    auto end_it = skyline.lower_bound(x + w);
    skyline.erase(start_it, end_it);

    skyline[x] = new_y;
    skyline[x + w] = h_after;
    
    auto it_x = skyline.find(x);
    if (it_x != skyline.begin() && std::prev(it_x)->second == it_x->second) {
        skyline.erase(it_x);
    }
    
    auto it_xw = skyline.find(x + w);
    if (it_xw != skyline.end() && it_xw != skyline.begin() && std::prev(it_xw)->second == it_xw->second) {
        skyline.erase(it_xw);
    }
}

// Main packing logic for a given item order
std::pair<std::vector<Placement>, long long> pack_strategy(
    const Bin& bin,
    const std::vector<ItemType>& item_types,
    const std::vector<ItemVariant>& variants) {
    
    std::vector<Placement> placements;
    long long total_profit = 0;
    std::map<int, int> remaining_limits;
    for (const auto& type : item_types) {
        remaining_limits[type.original_idx] = type.limit;
    }

    std::map<int, int> skyline;
    skyline[0] = 0;

    for (const auto& var : variants) {
        while (remaining_limits[var.type_idx] > 0) {
            auto [px, py] = find_best_pos(var.w, var.h, skyline, bin.W, bin.H);
            if (px != -1) {
                placements.push_back({item_types[var.type_idx].id, px, py, var.rot});
                total_profit += var.v;
                remaining_limits[var.type_idx]--;
                update_skyline(skyline, px, py, var.w, var.h);
            } else {
                break;
            }
        }
    }
    
    return {placements, total_profit};
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    json input_json;
    try {
        std::cin >> input_json;
    } catch (json::parse_error& e) {
        return 1;
    }

    Bin bin;
    bin.W = input_json["bin"]["W"];
    bin.H = input_json["bin"]["H"];
    bin.allow_rotate = input_json["bin"]["allow_rotate"];

    std::vector<ItemType> item_types;
    int idx_counter = 0;
    for (const auto& item_j : input_json["items"]) {
        item_types.push_back({
            item_j["type"],
            item_j["w"],
            item_j["h"],
            item_j["v"],
            item_j["limit"],
            idx_counter++
        });
    }

    std::vector<ItemVariant> variants;
    for (const auto& type : item_types) {
        long long area = (long long)type.w * type.h;
        variants.push_back({
            type.original_idx, type.w, type.h, type.v, false,
            (double)type.v / area,
            area,
            std::max(type.w, type.h),
            std::min(type.w, type.h),
            2 * (type.w + type.h)
        });
        if (bin.allow_rotate && type.w != type.h) {
            variants.push_back({
                type.original_idx, type.h, type.w, type.v, true,
                (double)type.v / area,
                area,
                std::max(type.w, type.h),
                std::min(type.w, type.h),
                2 * (type.w + type.h)
            });
        }
    }

    std::vector<std::function<bool(const ItemVariant&, const ItemVariant&)>> sorters;
    sorters.push_back([](const ItemVariant& a, const ItemVariant& b) { return a.density > b.density; });
    sorters.push_back([](const ItemVariant& a, const ItemVariant& b) { return a.max_dim > b.max_dim; });
    sorters.push_back([](const ItemVariant& a, const ItemVariant& b) { return a.area > b.area; });
    sorters.push_back([](const ItemVariant& a, const ItemVariant& b) { return a.h > b.h; });
    sorters.push_back([](const ItemVariant& a, const ItemVariant& b) { return a.w > b.w; });
    sorters.push_back([](const ItemVariant& a, const ItemVariant& b) { return a.perimeter > b.perimeter; });
    sorters.push_back([](const ItemVariant& a, const ItemVariant& b) {
        if (a.max_dim != b.max_dim) return a.max_dim > b.max_dim;
        return a.min_dim > b.min_dim;
    });

    std::vector<Placement> best_placements;
    long long max_profit = -1;

    for (auto& sorter : sorters) {
        std::vector<ItemVariant> sorted_variants = variants;
        std::sort(sorted_variants.begin(), sorted_variants.end(), sorter);
        
        auto [current_placements, current_profit] = pack_strategy(bin, item_types, sorted_variants);

        if (current_profit > max_profit) {
            max_profit = current_profit;
            best_placements = current_placements;
        }
    }

    json output_json;
    json placements_json = json::array();
    for (const auto& p : best_placements) {
        placements_json.push_back({
            {"type", p.id},
            {"x", p.x},
            {"y", p.y},
            {"rot", p.rot ? 1 : 0}
        });
    }
    output_json["placements"] = placements_json;

    std::cout << output_json.dump() << std::endl;

    return 0;
}
#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <list>
#include <functional>
#include <set>
#include <numeric>

// It's a common practice in competitive programming to include a single-header library like this.
#include "nlohmann/json.hpp"

using json = nlohmann::json;

// Data structures to represent problem entities
struct ItemType {
    std::string id;
    int w, h, v, limit;
    int original_idx;
};

struct AtomicItem {
    int w, h, v;
    int type_idx;
    bool rot;

    // Properties for sorting heuristics
    double density;
    int area;
    int max_dim;
};

struct Placement {
    std::string id;
    int x, y, rot;
};

struct PlacementCandidate {
    int x = -1, y = -1;
    bool isValid() const { return x != -1; }
};

class Solver {
private:
    int W, H;
    bool allow_rotate;
    std::vector<ItemType> item_types;

    std::vector<Placement> best_placements;
    long long best_profit = -1;

public:
    void parse_input() {
        json j;
        std::cin >> j;

        W = j["bin"]["W"];
        H = j["bin"]["H"];
        allow_rotate = j["bin"]["allow_rotate"];

        int idx = 0;
        for (const auto& item_json : j["items"]) {
            item_types.push_back({
                item_json["type"],
                item_json["w"],
                item_json["h"],
                item_json["v"],
                item_json["limit"],
                idx++
            });
        }
    }

    void solve() {
        std::vector<std::function<bool(const AtomicItem&, const AtomicItem&)>> sorters;
        sorters.push_back([](const AtomicItem& a, const AtomicItem& b){ return a.density > b.density; });
        sorters.push_back([](const AtomicItem& a, const AtomicItem& b){ return a.area > b.area; });
        sorters.push_back([](const AtomicItem& a, const AtomicItem& b){ return a.max_dim > b.max_dim; });
        sorters.push_back([](const AtomicItem& a, const AtomicItem& b){ if (a.h != b.h) return a.h > b.h; return a.w > b.w; });
        sorters.push_back([](const AtomicItem& a, const AtomicItem& b){ if (a.w != b.w) return a.w > b.w; return a.h > b.h; });
        
        for (const auto& sorter : sorters) {
            run_strategy(W, H, sorter, false);
            if (W != H && allow_rotate) {
                run_strategy(H, W, sorter, true);
            }
        }
    }

    void run_strategy(int current_W, int current_H, 
                      const std::function<bool(const AtomicItem&, const AtomicItem&)>& sorter, 
                      bool is_rotated_bin) {
        
        std::vector<AtomicItem> atomic_items;
        for (const auto& type : item_types) {
            atomic_items.push_back({
                type.w, type.h, type.v, type.original_idx, false,
                (double)type.v / (type.w * type.h),
                type.w * type.h,
                std::max(type.w, type.h)
            });
            if (allow_rotate && type.w != type.h) {
                atomic_items.push_back({
                    type.h, type.w, type.v, type.original_idx, true,
                    (double)type.v / (type.h * type.w),
                    type.h * type.w,
                    std::max(type.h, type.w)
                });
            }
        }
        std::sort(atomic_items.begin(), atomic_items.end(), sorter);

        std::vector<Placement> current_placements;
        long long current_profit = 0;
        std::vector<int> counts(item_types.size(), 0);
        std::map<int, int> skyline;
        skyline[0] = 0;

        while (true) {
            bool placed_in_iteration = false;
            int best_atomic_item_idx = -1;
            PlacementCandidate best_cand;

            for (int i = 0; i < atomic_items.size(); ++i) {
                const auto& item = atomic_items[i];
                if (counts[item.type_idx] >= item_types[item.type_idx].limit) continue;

                PlacementCandidate cand = find_best_placement(item.w, item.h, current_W, current_H, skyline);
                if (cand.isValid()) {
                    best_atomic_item_idx = i;
                    best_cand = cand;
                    placed_in_iteration = true;
                    break;
                }
            }
            
            if (placed_in_iteration) {
                const auto& item = atomic_items[best_atomic_item_idx];
                current_placements.push_back({item_types[item.type_idx].id, best_cand.x, best_cand.y, item.rot});
                current_profit += item.v;
                counts[item.type_idx]++;
                update_skyline(best_cand.x, best_cand.y, item.w, item.h, skyline);
            } else {
                break;
            }
        }

        if (current_profit > best_profit) {
            best_profit = current_profit;
            if (is_rotated_bin) {
                best_placements.clear();
                for (const auto& p : current_placements) {
                    best_placements.push_back({p.id, p.y, p.x, 1 - p.rot});
                }
            } else {
                best_placements = current_placements;
            }
        }
    }

    PlacementCandidate find_best_placement(int w, int h, int current_W, int current_H, const std::map<int, int>& skyline) {
        PlacementCandidate best_cand;
        int min_y = current_H + 1;

        std::set<int> candidate_x_set;
        for(auto const& [x_coord, y_coord] : skyline) {
            candidate_x_set.insert(x_coord);
            if(x_coord >= w) candidate_x_set.insert(x_coord - w);
        }

        for (int x : candidate_x_set) {
            if (x + w > current_W) continue;
            
            auto it = skyline.upper_bound(x);
            --it;

            int base_y = 0;
            auto temp_it = it;
            while (temp_it != skyline.end() && temp_it->first < x + w) {
                base_y = std::max(base_y, temp_it->second);
                ++temp_it;
            }

            if (base_y + h <= current_H) {
                if (base_y < min_y) {
                    min_y = base_y;
                    best_cand.x = x;
                    best_cand.y = base_y;
                }
            }
        }
        return best_cand;
    }

    void update_skyline(int x, int y, int w, int h, std::map<int, int>& skyline) {
        int new_y = y + h;
        int x2 = x + w;

        auto it = skyline.upper_bound(x2);
        int h_after = std::prev(it)->second;

        auto erase_it = skyline.lower_bound(x);
        while(erase_it != skyline.end() && erase_it->first < x2) {
            erase_it = skyline.erase(erase_it);
        }
        
        skyline[x] = new_y;
        if (skyline.find(x2) == skyline.end() || skyline.at(x2) < h_after) {
             skyline[x2] = h_after;
        }

        it = skyline.find(x2);
        if (it != skyline.end() && it != skyline.begin() && std::prev(it)->second == it->second) {
            skyline.erase(it);
        }

        it = skyline.find(x);
        if (it != skyline.begin() && std::prev(it)->second == it->second) {
            skyline.erase(it);
        }
    }

    void print_output() {
        if(best_profit == -1) {
            json out;
            out["placements"] = json::array();
            std::cout << out.dump(2) << std::endl;
            return;
        }

        json out;
        json& placements_json = out["placements"];
        placements_json = json::array();
        for (const auto& p : best_placements) {
            json p_json;
            p_json["type"] = p.id;
            p_json["x"] = p.x;
            p_json["y"] = p.y;
            p_json["rot"] = p.rot;
            placements_json.push_back(p_json);
        }
        std::cout << out.dump(2) << std::endl;
    }
};

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    Solver solver;
    solver.parse_input();
    solver.solve();
    solver.print_output();
    return 0;
}
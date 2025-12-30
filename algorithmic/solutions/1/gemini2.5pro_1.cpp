#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <cmath>
#include <functional>
#include <numeric>

#include "nlohmann/json.hpp"

using json = nlohmann::json;

const long long MAX_MASS = 20000000;
const long long MAX_VOLUME = 25000000;

struct Item {
    std::string name;
    int q;
    long long v, m, l;
};

struct Solution {
    std::vector<int> counts;
    long long value = 0;
    long long mass = 0;
    long long volume = 0;

    Solution(int num_items) : counts(num_items, 0) {}
};

void calculate_stats(const std::vector<Item>& items, Solution& sol) {
    sol.value = 0;
    sol.mass = 0;
    sol.volume = 0;
    for (size_t i = 0; i < items.size(); ++i) {
        sol.value += (long long)sol.counts[i] * items[i].v;
        sol.mass += (long long)sol.counts[i] * items[i].m;
        sol.volume += (long long)sol.counts[i] * items[i].l;
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    json input_json;
    std::cin >> input_json;

    std::vector<Item> items;
    for (auto& [key, val] : input_json.items()) {
        items.push_back({
            key,
            val[0].get<int>(),
            val[1].get<long long>(),
            val[2].get<long long>(),
            val[3].get<long long>()
        });
    }
    
    int num_items = items.size();

    // --- Greedy Phase ---
    std::vector<Solution> initial_solutions;

    std::vector<std::function<double(const Item&)>> metrics;
    metrics.push_back([](const Item& i){ return i.m > 0 ? (double)i.v / i.m : (i.v > 0 ? 1e18 : 0); });
    metrics.push_back([](const Item& i){ return i.l > 0 ? (double)i.v / i.l : (i.v > 0 ? 1e18 : 0); });
    metrics.push_back([](const Item& i){ return (i.m + i.l) > 0 ? (double)i.v / (double)(i.m + i.l) : (i.v > 0 ? 1e18 : 0); });
    metrics.push_back([](const Item& i){ return (double)i.v; });
    metrics.push_back([](const Item& i){ 
        double norm_res = (double)i.m / MAX_MASS + (double)i.l / MAX_VOLUME;
        return norm_res > 1e-9 ? (double)i.v / norm_res : (i.v > 0 ? 1e18 : 0);
    });

    struct IndividualItem {
        double metric_val;
        int type_idx;
    };

    for (const auto& metric : metrics) {
        Solution sol(num_items);
        std::vector<IndividualItem> all_items_list;
        for (int i = 0; i < num_items; ++i) {
            if (items[i].m <= 0 && items[i].l <= 0) continue;
            double mval = metric(items[i]);
            for (int j = 0; j < items[i].q; ++j) {
                all_items_list.push_back({mval, i});
            }
        }

        std::sort(all_items_list.begin(), all_items_list.end(), [](const IndividualItem& a, const IndividualItem& b){
            return a.metric_val > b.metric_val;
        });
        
        // This greedy approach packs items one by one.
        // It's more granular than packing in chunks.
        for (const auto& indiv_item : all_items_list) {
            int idx = indiv_item.type_idx;
            if (sol.mass + items[idx].m <= MAX_MASS && sol.volume + items[idx].l <= MAX_VOLUME) {
                sol.counts[idx]++;
                sol.mass += items[idx].m;
                sol.volume += items[idx].l;
                sol.value += items[idx].v;
            }
        }
        initial_solutions.push_back(sol);
    }
    
    Solution best_sol(num_items);
    if (!initial_solutions.empty()) {
        best_sol = *std::max_element(initial_solutions.begin(), initial_solutions.end(), 
            [](const Solution& a, const Solution& b){
                return a.value < b.value;
            });
    }

    // --- Local Search Phase (Steepest Ascent Hill Climbing) ---
    bool improved = true;
    while(improved) {
        improved = false;
        long long best_val_change = 0;
        int move_type = -1; // 0: add, 1: swap
        int add_idx = -1, rem_idx = -1;

        // Try adding one item
        for (int i = 0; i < num_items; ++i) {
            if (best_sol.counts[i] < items[i].q &&
                best_sol.mass + items[i].m <= MAX_MASS &&
                best_sol.volume + items[i].l <= MAX_VOLUME) {
                if (items[i].v > best_val_change) {
                    best_val_change = items[i].v;
                    move_type = 0;
                    add_idx = i;
                }
            }
        }
        
        // Try swapping one item for another
        for (int i = 0; i < num_items; ++i) { // item to remove
            if (best_sol.counts[i] == 0) continue;
            for (int j = 0; j < num_items; ++j) { // item to add
                if (i == j || best_sol.counts[j] >= items[j].q) continue;

                long long next_mass = best_sol.mass - items[i].m + items[j].m;
                long long next_vol = best_sol.volume - items[i].l + items[j].l;

                if (next_mass <= MAX_MASS && next_vol <= MAX_VOLUME) {
                    long long val_change = items[j].v - items[i].v;
                    if (val_change > best_val_change) {
                        best_val_change = val_change;
                        move_type = 1;
                        rem_idx = i;
                        add_idx = j;
                    }
                }
            }
        }

        if (best_val_change > 0) {
            improved = true;
            if (move_type == 0) { // Add
                best_sol.counts[add_idx]++;
            } else if (move_type == 1) { // Swap
                best_sol.counts[rem_idx]--;
                best_sol.counts[add_idx]++;
            }
            calculate_stats(items, best_sol);
        }
    }

    // --- Output ---
    json output_json;
    for (int i = 0; i < num_items; ++i) {
        output_json[items[i].name] = best_sol.counts[i];
    }
    std::cout << output_json.dump(2) << std::endl;

    return 0;
}
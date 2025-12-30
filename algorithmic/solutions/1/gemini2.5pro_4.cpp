#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <set>
#include <random>
#include <chrono>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

struct Item {
    std::string name;
    int q;
    long long v, m, l;
    double density;
    int original_idx;
};

// Global constants
const long long MAX_MASS = 20000000;
const long long MAX_VOL = 25000000;

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    json input_json;
    std::cin >> input_json;

    std::vector<Item> original_items;
    std::vector<std::string> key_order;
    int idx_counter = 0;
    for (auto& el : input_json.items()) {
        key_order.push_back(el.key());
        auto& props = el.value();
        original_items.push_back({
            el.key(),
            (int)props[0],
            (long long)props[1],
            (long long)props[2],
            (long long)props[3],
            0.0,
            idx_counter++
        });
    }

    std::set<double> c_values_set;
    c_values_set.insert(0.0);
    c_values_set.insert(1.0);
    for (size_t i = 0; i < original_items.size(); ++i) {
        for (size_t j = i + 1; j < original_items.size(); ++j) {
            auto& item1 = original_items[i];
            auto& item2 = original_items[j];
            long long v1 = item1.v, m1 = item1.m, l1 = item1.l;
            long long v2 = item2.v, m2 = item2.m, l2 = item2.l;
            
            double num = (double)v2 * l1 - (double)v1 * l2;
            double den = (double)v1 * (m2 - l2) - (double)v2 * (m1 - l1);

            if (std::abs(den) > 1e-9) {
                double c = num / den;
                if (c > 1e-9 && c < 1.0 - 1e-9) {
                    c_values_set.insert(c);
                }
            }
        }
    }
    
    std::vector<double> test_cs;
    for (double c : c_values_set) {
        test_cs.push_back(c);
        if (c > 1e-9) test_cs.push_back(c - 1e-9);
        if (c < 1.0 - 1e-9) test_cs.push_back(c + 1e-9);
    }
    std::sort(test_cs.begin(), test_cs.end());
    test_cs.erase(std::unique(test_cs.begin(), test_cs.end()), test_cs.end());

    long long best_total_value = -1;
    std::vector<int> best_counts(original_items.size());
    double best_c = -1.0;
    
    for (double c : test_cs) {
        if (c < 0 || c > 1) continue;
        std::vector<Item> current_items = original_items;
        for (auto& item : current_items) {
            double cost = c * item.m + (1.0 - c) * item.l;
            if (cost < 1e-9) {
                item.density = 1e18; // Effectively infinite
            } else {
                item.density = (double)item.v / cost;
            }
        }
        
        std::sort(current_items.begin(), current_items.end(), [](const Item& a, const Item& b) {
            return a.density > b.density;
        });

        long long current_m = 0;
        long long current_l = 0;
        long long current_v = 0;
        std::vector<int> current_counts(original_items.size(), 0);

        for (const auto& item : current_items) {
            long long can_take = item.q;
            if (item.m > 0) can_take = std::min(can_take, (MAX_MASS - current_m) / item.m);
            if (item.l > 0) can_take = std::min(can_take, (MAX_VOL - current_l) / item.l);
            
            if (can_take > 0) {
                current_m += can_take * item.m;
                current_l += can_take * item.l;
                current_v += can_take * item.v;
                current_counts[item.original_idx] = can_take;
            }
        }

        if (current_v > best_total_value) {
            best_total_value = current_v;
            best_counts = current_counts;
            best_c = c;
        }
    }

    // Local Search to improve the best solution
    if (best_c >= 0) {
        std::vector<Item> sorted_by_best_c = original_items;
        for (auto& item : sorted_by_best_c) {
            double cost = best_c * item.m + (1.0 - best_c) * item.l;
            if (cost < 1e-9) item.density = 1e18;
            else item.density = (double)item.v / cost;
        }
        std::sort(sorted_by_best_c.begin(), sorted_by_best_c.end(), [](const Item& a, const Item& b) {
            return a.density > b.density;
        });

        long long current_m = 0;
        long long current_l = 0;
        for (size_t i = 0; i < original_items.size(); ++i) {
            current_m += (long long)best_counts[i] * original_items[i].m;
            current_l += (long long)best_counts[i] * original_items[i].l;
        }
        
        std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
        
        // Iteration limit is heuristic.
        for (int iter = 0; iter < 100000; ++iter) {
            std::vector<int> present_items_indices;
            for (size_t i = 0; i < best_counts.size(); ++i) {
                if (best_counts[i] > 0) {
                    present_items_indices.push_back(i);
                }
            }
            if (present_items_indices.empty()) break;

            std::uniform_int_distribution<int> dist(0, present_items_indices.size() - 1);
            int idx_to_remove = present_items_indices[dist(rng)];

            long long temp_m = current_m - original_items[idx_to_remove].m;
            long long temp_l = current_l - original_items[idx_to_remove].l;
            long long temp_v = best_total_value - original_items[idx_to_remove].v;
            std::vector<int> temp_counts = best_counts;
            temp_counts[idx_to_remove]--;
            
            for (const auto& item : sorted_by_best_c) {
                long long can_take = item.q - temp_counts[item.original_idx];
                if (can_take <= 0) continue;
                if (item.m > 0) can_take = std::min(can_take, (MAX_MASS - temp_m) / item.m);
                if (item.l > 0) can_take = std::min(can_take, (MAX_VOL - temp_l) / item.l);
                
                if (can_take > 0) {
                    temp_m += can_take * item.m;
                    temp_l += can_take * item.l;
                    temp_v += can_take * item.v;
                    temp_counts[item.original_idx] += can_take;
                }
            }
            
            if (temp_v > best_total_value) {
                best_total_value = temp_v;
                best_counts = temp_counts;
                current_m = temp_m;
                current_l = temp_l;
            }
        }
    }
    
    json output_json;
    for (const auto& key : key_order) {
        bool found = false;
        for (size_t i=0; i < original_items.size(); ++i) {
            if (original_items[i].name == key) {
                output_json[key] = best_counts[i];
                found = true;
                break;
            }
        }
    }
    
    std::cout << output_json.dump(2) << std::endl;

    return 0;
}
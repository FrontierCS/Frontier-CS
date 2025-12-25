#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <map>
#include <functional>

// To create a single-file solution, the content of nlohmann/json.hpp is included here.
// This is a placeholder for the actual header content.
#ifndef NLOHMANN_JSON_HPP
#include "json.hpp" // Assumes json.hpp is in the same directory or in include path.
#endif


using json = nlohmann::json;
using ll = long long;

const ll M_CAP = 20000000;
const ll L_CAP = 25000000;

struct Item {
    std::string name;
    int id;
    int q;
    ll v, m, l;
    double density;
};

std::vector<Item> all_items;
std::vector<Item> large_items, small_items;

ll max_total_value = -1;
std::vector<int> best_counts;

ll states_visited = 0;
const ll MAX_STATES_PER_RUN = 5000000;

void solve(int large_item_idx, ll current_m, ll current_l, ll current_v, std::vector<int>& current_counts) {
    if (states_visited++ > MAX_STATES_PER_RUN) {
        return;
    }

    if (large_item_idx == large_items.size()) {
        ll rem_m = M_CAP - current_m;
        ll rem_l = L_CAP - current_l;
        ll total_v = current_v;
        
        std::vector<int> final_counts = current_counts;

        for (const auto& s_item : small_items) {
            final_counts[s_item.id] = 0; // Ensure small item counts are reset for this path
            if (s_item.m <= 0 && s_item.l <= 0) continue;
            
            ll can_take = s_item.q;
            if (s_item.m > 0) can_take = std::min(can_take, rem_m / s_item.m);
            if (s_item.l > 0) can_take = std::min(can_take, rem_l / s_item.l);
            
            if (can_take > 0) {
                rem_m -= can_take * s_item.m;
                rem_l -= can_take * s_item.l;
                total_v += can_take * s_item.v;
                final_counts[s_item.id] = can_take;
            }
        }

        if (total_v > max_total_value) {
            max_total_value = total_v;
            best_counts = final_counts;
        }
        return;
    }

    const auto& l_item = large_items[large_item_idx];
    ll max_k = l_item.q;
    if (l_item.m > 0) max_k = std::min(max_k, (M_CAP - current_m) / l_item.m);
    if (l_item.l > 0) max_k = std::min(max_k, (L_CAP - current_l) / l_item.l);

    for (ll k = max_k; k >= 0; --k) { // Iterate downwards to prioritize fuller bags
        current_counts[l_item.id] = k;
        solve(large_item_idx + 1,
              current_m + k * l_item.m,
              current_l + k * l_item.l,
              current_v + k * l_item.v,
              current_counts);
        if (states_visited > MAX_STATES_PER_RUN) return;
    }
    current_counts[l_item.id] = 0;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    json input;
    std::cin >> input;

    int current_id = 0;
    for (auto const& [name, val] : input.items()) {
        all_items.push_back({
            name,
            current_id++,
            val[0].get<int>(),
            val[1].get<ll>(),
            val[2].get<ll>(),
            val[3].get<ll>(),
            0.0
        });
    }

    ll m_thresh = M_CAP / 40;
    ll l_thresh = L_CAP / 40;
    for (const auto& item : all_items) {
        if (item.m > m_thresh || item.l > l_thresh) {
            large_items.push_back(item);
        } else {
            small_items.push_back(item);
        }
    }
    
    best_counts.resize(all_items.size(), 0);
    std::vector<int> current_counts(all_items.size(), 0);

    for (int i = 0; i <= 10; ++i) {
        double alpha = i / 10.0;
        
        for (auto& item : small_items) {
            if (alpha < 1e-9) {
                item.density = (item.l > 0) ? (double)item.v / item.l : 1e18;
            } else if (alpha > 1.0 - 1e-9) {
                item.density = (item.m > 0) ? (double)item.v / item.m : 1e18;
            } else {
                double normalized_cost = alpha * (double)item.m / M_CAP + (1.0 - alpha) * (double)item.l / L_CAP;
                item.density = (normalized_cost > 1e-12) ? (double)item.v / normalized_cost : 1e18;
            }
        }

        std::sort(small_items.begin(), small_items.end(), [&](const Item& a, const Item& b) {
            return a.density > b.density;
        });
        
        states_visited = 0;
        solve(0, 0, 0, 0, current_counts);
    }
    
    auto run_greedy = [&](auto density_func) {
        std::vector<Item> sorted_items = all_items;
        std::sort(sorted_items.begin(), sorted_items.end(), [&](const Item& a, const Item& b) {
            return density_func(a) > density_func(b);
        });

        std::vector<int> greedy_counts(all_items.size(), 0);
        ll current_m = 0, current_l = 0, current_v = 0;
        
        for (const auto& item : sorted_items) {
            ll rem_m = M_CAP - current_m;
            ll rem_l = L_CAP - current_l;
            ll can_take = item.q;
            if (item.m > 0) can_take = std::min(can_take, rem_m / item.m);
            if (item.l > 0) can_take = std::min(can_take, rem_l / item.l);

            if(can_take > 0) {
                current_m += can_take * item.m;
                current_l += can_take * item.l;
                current_v += can_take * item.v;
                greedy_counts[item.id] = can_take;
            }
        }
        if (current_v > max_total_value) {
            max_total_value = current_v;
            best_counts = greedy_counts;
        }
    };

    run_greedy([](const Item& i) { return (i.m > 0) ? (double)i.v / i.m : 1e18; });
    run_greedy([](const Item& i) { return (i.l > 0) ? (double)i.v / i.l : 1e18; });
    run_greedy([](const Item& i) { return (i.m + i.l > 0) ? (double)i.v / (double)(i.m + i.l) : 1e18; });

    json output;
    for (const auto& item : all_items) {
        output[item.name] = best_counts[item.id];
    }
    std::cout << output.dump(2) << std::endl;

    return 0;
}
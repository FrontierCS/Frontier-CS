#include <iostream>
#include <string>
#include <vector>
#include <map>
#include <algorithm>
#include <array>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

const long long W_MASS = 20000000;
const long long W_VOL = 25000000;
const int N_ITEMS = 12;

struct Item {
    std::string name;
    int q;
    long long v, m, l;
    int original_idx;
};

struct State {
    long long m = 0, l = 0, v = 0;
    std::vector<int> counts;

    bool operator<(const State& other) const {
        if (m != other.m) return m < other.m;
        if (l != other.l) return l < other.l;
        return v > other.v; // for sorting, higher value is better
    }
};

std::vector<State> prune(std::vector<State>& states) {
    if (states.size() <= 1) return states;
    
    std::sort(states.begin(), states.end(), [](const State& a, const State& b){
        return a.v > b.v;
    });

    std::vector<State> final_pruned;
    final_pruned.reserve(states.size());

    for(const auto& s : states) {
        bool dominated = false;
        for(const auto& p : final_pruned) {
            if (p.m <= s.m && p.l <= s.l) { // p.v >= s.v is guaranteed by sort order
                dominated = true;
                break;
            }
        }
        if (!dominated) {
            final_pruned.push_back(s);
        }
    }
    return final_pruned;
}

std::vector<State> generate_states(const std::vector<Item>& items, int state_limit) {
    int n = items.size();
    if (n == 0) {
        std::vector<State> res;
        res.emplace_back();
        res.back().counts.resize(0);
        return res;
    }

    std::vector<State> states;
    states.emplace_back();
    states.back().counts.resize(n, 0);

    for (int i = 0; i < n; ++i) {
        std::vector<State> next_states;
        int q_eff = items[i].q;
        // Heuristic cap to prevent state explosion
        if (q_eff > 30) q_eff = 30;

        next_states.reserve(states.size() * (q_eff + 1));

        for (const auto& s : states) {
            for (int c = 0; c <= q_eff; ++c) {
                long long next_m = s.m + c * items[i].m;
                long long next_l = s.l + c * items[i].l;
                if (next_m > W_MASS || next_l > W_VOL) {
                    break;
                }
                State next_s;
                next_s.m = next_m;
                next_s.l = next_l;
                next_s.v = s.v + c * items[i].v;
                next_s.counts = s.counts;
                next_s.counts[i] = c;
                next_states.push_back(next_s);
            }
        }
        
        states = prune(next_states);
        if (states.size() > state_limit) {
            std::sort(states.begin(), states.end(), [](const State& a, const State& b){
                return a.v > b.v;
            });
            states.resize(state_limit);
        }
    }
    return states;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    json input_json;
    std::cin >> input_json;

    std::vector<Item> all_items;
    int idx_counter = 0;
    for (auto& [name, val] : input_json.items()) {
        all_items.push_back({
            name,
            val[0].get<int>(),
            val[1].get<long long>(),
            val[2].get<long long>(),
            val[3].get<long long>(),
            idx_counter++
        });
    }

    std::vector<Item> lumpy_items, dust_items;
    
    for (const auto& item : all_items) {
        if (item.q > 50 && (item.m < 100000 || item.l < 100000)) {
            dust_items.push_back(item);
        } else {
            lumpy_items.push_back(item);
        }
    }

    std::sort(dust_items.begin(), dust_items.end(), [](const Item& a, const Item& b) {
        double dens_a = (double)a.v / (a.m / (double)W_MASS * 0.5 + a.l / (double)W_VOL * 0.5 + 1e-9);
        double dens_b = (double)b.v / (b.m / (double)W_MASS * 0.5 + b.l / (double)W_VOL * 0.5 + 1e-9);
        return dens_a > dens_b;
    });

    std::vector<Item> lumpy_a, lumpy_b;
    for (size_t i = 0; i < lumpy_items.size(); ++i) {
        if (i < lumpy_items.size() / 2) {
            lumpy_a.push_back(lumpy_items[i]);
        } else {
            lumpy_b.push_back(lumpy_items[i]);
        }
    }
    
    int state_limit = 4000;
    auto states_a = generate_states(lumpy_a, state_limit);
    auto states_b = generate_states(lumpy_b, state_limit);

    long long max_total_value = -1;
    std::vector<int> best_counts(N_ITEMS, 0);

    for (const auto& s_a : states_a) {
        for (const auto& s_b : states_b) {
            long long current_m = s_a.m + s_b.m;
            long long current_l = s_a.l + s_b.l;

            if (current_m > W_MASS || current_l > W_VOL) continue;

            long long current_v = s_a.v + s_b.v;
            std::vector<int> current_counts(N_ITEMS, 0);

            for (size_t i = 0; i < lumpy_a.size(); ++i) current_counts[lumpy_a[i].original_idx] = s_a.counts[i];
            for (size_t i = 0; i < lumpy_b.size(); ++i) current_counts[lumpy_b[i].original_idx] = s_b.counts[i];
            
            long long m_rem = W_MASS - current_m;
            long long l_rem = W_VOL - current_l;
            long long dust_v = 0;
            
            for (const auto& item : dust_items) {
                int num_to_take = item.q;
                if (item.m > 0) num_to_take = std::min(num_to_take, (int)(m_rem / item.m));
                if (item.l > 0) num_to_take = std::min(num_to_take, (int)(l_rem / item.l));
                
                if (num_to_take > 0) {
                    m_rem -= (long long)num_to_take * item.m;
                    l_rem -= (long long)num_to_take * item.l;
                    dust_v += (long long)num_to_take * item.v;
                    current_counts[item.original_idx] += num_to_take;
                }
            }
            
            if (current_v + dust_v > max_total_value) {
                max_total_value = current_v + dust_v;
                best_counts = current_counts;
            }
        }
    }

    // A pure greedy solution on all items as a baseline
    {
        long long m_rem = W_MASS;
        long long l_rem = W_VOL;
        long long current_v = 0;
        std::vector<int> current_counts(N_ITEMS, 0);
        std::vector<Item> sorted_all = all_items;
        std::sort(sorted_all.begin(), sorted_all.end(), [](const Item& a, const Item& b) {
            double dens_a = (double)a.v / (a.m / (double)W_MASS * 0.5 + a.l / (double)W_VOL * 0.5 + 1e-9);
            double dens_b = (double)b.v / (b.m / (double)W_MASS * 0.5 + b.l / (double)W_VOL * 0.5 + 1e-9);
            return dens_a > dens_b;
        });

        for (const auto& item : sorted_all) {
             int num_to_take = item.q;
             if (item.m > 0) num_to_take = std::min(num_to_take, (int)(m_rem / item.m));
             if (item.l > 0) num_to_take = std::min(num_to_take, (int)(l_rem / item.l));
             
             if (num_to_take > 0) {
                 m_rem -= (long long)num_to_take * item.m;
                 l_rem -= (long long)num_to_take * item.l;
                 current_v += (long long)num_to_take * item.v;
                 current_counts[item.original_idx] = num_to_take;
             }
        }
        if (current_v > max_total_value) {
            best_counts = current_counts;
        }
    }

    json output_json;
    for (int i = 0; i < N_ITEMS; ++i) {
        output_json[all_items[i].name] = best_counts[i];
    }

    std::cout << output_json.dump(1, '\t') << std::endl;

    return 0;
}
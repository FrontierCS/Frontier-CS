#include <iostream>
#include <vector>
#include <string>
#include <array>
#include <unordered_map>
#include <algorithm>
#include <utility>
#include "json.hpp"

using json = nlohmann::json;

const long long MAX_MASS = 20000000;
const long long MAX_VOLUME = 25000000;
const int NUM_ITEMS = 12;
const int HALF_NUM_ITEMS = 6;

struct Item {
    std::string name;
    int q;
    long long v, m, l;
    int original_idx;
};

struct State {
    long long m, l, v;
    std::array<int, HALF_NUM_ITEMS> counts;
};

struct pair_hash {
    template <class T1, class T2>
    std::size_t operator () (const std::pair<T1, T2>& p) const {
        auto h1 = std::hash<T1>{}(p.first);
        auto h2 = std::hash<T2>{}(p.second);
        // A simple way to combine hashes, found to be effective in practice.
        return h1 ^ (h2 << 1);
    }
};

using StatesMap = std::unordered_map<std::pair<long long, long long>, std::pair<long long, std::array<int, HALF_NUM_ITEMS>>, pair_hash>;

StatesMap generate_states(const std::vector<Item>& items) {
    StatesMap states;
    states.reserve(100000); // Pre-allocation to reduce rehashes
    states[{0, 0}] = {0, {}};

    for (int i = 0; i < items.size(); ++i) {
        const auto& item = items[i];
        long long current_q = item.q;
        
        std::vector<long long> meta_quantities;
        for (long long p = 1; current_q > 0; p *= 2) {
            long long take = std::min(p, current_q);
            meta_quantities.push_back(take);
            current_q -= take;
        }

        for (const auto& k : meta_quantities) {
            long long delta_m = k * item.m;
            long long delta_l = k * item.l;
            long long delta_v = k * item.v;

            std::vector<std::pair<std::pair<long long, long long>, std::pair<long long, std::array<int, HALF_NUM_ITEMS>>>> updates;
            updates.reserve(states.size());

            for (const auto& s : states) {
                long long new_m = s.first.first + delta_m;
                long long new_l = s.first.second + delta_l;

                if (new_m <= MAX_MASS && new_l <= MAX_VOLUME) {
                    long long new_v = s.second.first + delta_v;
                    auto new_counts = s.second.second;
                    new_counts[i] += k;
                    updates.push_back({{new_m, new_l}, {new_v, new_counts}});
                }
            }
            
            for (const auto& update : updates) {
                const auto& key = update.first;
                const auto& val = update.second;
                auto it = states.find(key);
                if (it == states.end() || it->second.first < val.first) {
                    states[key] = val;
                }
            }
        }
    }
    return states;
}

std::vector<State> prune_and_convert(const StatesMap& states_map) {
    std::vector<State> states_vec;
    states_vec.reserve(states_map.size());
    for (const auto& pair : states_map) {
        states_vec.push_back({pair.first.first, pair.first.second, pair.second.first, pair.second.second});
    }

    std::sort(states_vec.begin(), states_vec.end(), [](const State& a, const State& b) {
        if (a.m != b.m) return a.m < b.m;
        if (a.l != b.l) return a.l < b.l;
        return a.v > b.v;
    });

    std::vector<State> pruned;
    pruned.reserve(states_vec.size());
    for (const auto& s : states_vec) {
        while (!pruned.empty() && pruned.back().l >= s.l && pruned.back().v <= s.v) {
            pruned.pop_back();
        }
        if (pruned.empty() || pruned.back().l < s.l || pruned.back().v < s.v) {
            pruned.push_back(s);
        }
    }
    return pruned;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    json input_json;
    std::cin >> input_json;

    std::vector<Item> all_items;
    int idx = 0;
    for (auto& [key, value] : input_json.items()) {
        all_items.push_back({key, value[0], value[1], value[2], value[3], idx++});
    }
    
    std::sort(all_items.begin(), all_items.end(), [](const Item& a, const Item& b){
        return a.name < b.name;
    });

    std::vector<Item> groupA(all_items.begin(), all_items.begin() + HALF_NUM_ITEMS);
    std::vector<Item> groupB(all_items.begin() + HALF_NUM_ITEMS, all_items.end());

    StatesMap states_map_A = generate_states(groupA);
    StatesMap states_map_B = generate_states(groupB);
    
    std::vector<State> listA = prune_and_convert(states_map_A);
    std::vector<State> listB = prune_and_convert(states_map_B);
    
    std::sort(listA.begin(), listA.end(), [](const State& a, const State& b) {
        return a.m < b.m;
    });
    std::sort(listB.begin(), listB.end(), [](const State& a, const State& b) {
        return a.m < b.m;
    });

    long long max_val = 0;
    std::array<int, NUM_ITEMS> best_counts = {};

    int ptrB = listB.size() - 1;
    for (const auto& s_a : listA) {
        while (ptrB >= 0 && s_a.m + listB[ptrB].m > MAX_MASS) {
            ptrB--;
        }
        if (ptrB < 0) {
            break;
        }

        for (int i = 0; i <= ptrB; ++i) {
            const auto& s_b = listB[i];
            if (s_a.l + s_b.l <= MAX_VOLUME) {
                if (s_a.v + s_b.v > max_val) {
                    max_val = s_a.v + s_b.v;
                    for (int j = 0; j < HALF_NUM_ITEMS; ++j) {
                        best_counts[groupA[j].original_idx] = s_a.counts[j];
                    }
                    for (int j = 0; j < HALF_NUM_ITEMS; ++j) {
                        best_counts[groupB[j].original_idx] = s_b.counts[j];
                    }
                }
            }
        }
    }

    json output_json;
    for(int i = 0; i < NUM_ITEMS; ++i) {
        output_json[all_items[i].name] = best_counts[i];
    }
    std::cout << output_json.dump(1, '\t') << std::endl;

    return 0;
}
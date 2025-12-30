#include <iostream>
#include <string>
#include <vector>
#include <unordered_map>
#include <algorithm>

using namespace std;

const long long M_MAX = 20000000;   // 20 kg in mg
const long long V_MAX = 25000000;   // 25 liters in µL

struct BinaryItem {
    long long mass;
    long long volume;
    long long value;
    int category;
    int copies;
};

struct State {
    long long volume;
    long long value;
    int prev_item;      // index in binary_items
    long long prev_mass;
};

int main() {
    // Read the whole input
    string input;
    char c;
    while (cin.get(c)) input += c;

    // Parse JSON
    vector<string> categories;
    vector<long long> q, v, m, l;
    size_t pos = 0;
    while (pos < input.size() && input[pos] != '{') ++pos;
    ++pos; // skip '{'
    for (int i = 0; i < 12; ++i) {
        // Key
        while (pos < input.size() && input[pos] != '"') ++pos;
        size_t start_key = pos + 1;
        ++pos;
        while (pos < input.size() && input[pos] != '"') ++pos;
        string key = input.substr(start_key, pos - start_key);
        categories.push_back(key);
        ++pos; // skip '"'

        // Skip to '['
        while (pos < input.size() && input[pos] != '[') ++pos;
        ++pos;

        // Four integers
        long long nums[4];
        for (int j = 0; j < 4; ++j) {
            while (pos < input.size() && (input[pos] < '0' || input[pos] > '9')) ++pos;
            size_t start_num = pos;
            while (pos < input.size() && input[pos] >= '0' && input[pos] <= '9') ++pos;
            nums[j] = stoll(input.substr(start_num, pos - start_num));
            if (j < 3) {
                while (pos < input.size() && input[pos] != ',') ++pos;
                ++pos;
            }
        }
        q.push_back(nums[0]);
        v.push_back(nums[1]);
        m.push_back(nums[2]);
        l.push_back(nums[3]);

        // Skip ']'
        while (pos < input.size() && input[pos] != ']') ++pos;
        ++pos;
        // Skip whitespace and comma (or '}')
        while (pos < input.size() && (input[pos] == ' ' || input[pos] == '\n' || input[pos] == '\r' || input[pos] == '\t'))
            ++pos;
        if (i < 11 && input[pos] == ',') ++pos;
    }

    // Build binary items (bounded knapsack -> 0/1 via powers of two)
    vector<BinaryItem> binary_items;
    int cat_count = categories.size();
    for (int i = 0; i < cat_count; ++i) {
        long long quantity = q[i];
        int mult = 1;
        while (quantity > 0) {
            long long take = min((long long)mult, quantity);
            binary_items.push_back({
                take * m[i],
                take * l[i],
                take * v[i],
                i,
                (int)take
            });
            quantity -= take;
            mult <<= 1;
        }
    }

    // Sparse DP: map mass -> best state (volume, value, back pointer)
    unordered_map<long long, State> dp;
    dp[0] = {0, 0, -1, -1};
    long long best_value = 0;
    long long best_mass = 0;

    int item_count = binary_items.size();
    for (int idx = 0; idx < item_count; ++idx) {
        const BinaryItem& it = binary_items[idx];
        unordered_map<long long, State> updates;

        for (const auto& entry : dp) {
            long long old_mass = entry.first;
            const State& s = entry.second;

            long long new_mass = old_mass + it.mass;
            if (new_mass > M_MAX) continue;
            long long new_volume = s.volume + it.volume;
            if (new_volume > V_MAX) continue;
            long long new_value = s.value + it.value;

            bool better = false;
            auto cur_it = dp.find(new_mass);
            if (cur_it == dp.end()) {
                better = true;
            } else {
                const State& cur = cur_it->second;
                if (new_value > cur.value ||
                    (new_value == cur.value && new_volume < cur.volume))
                    better = true;
            }

            if (better) {
                auto upd_it = updates.find(new_mass);
                if (upd_it == updates.end() ||
                    new_value > upd_it->second.value ||
                    (new_value == upd_it->second.value && new_volume < upd_it->second.volume))
                {
                    updates[new_mass] = {new_volume, new_value, idx, old_mass};
                }
            }
        }

        // Merge updates into dp
        for (const auto& p : updates) {
            dp[p.first] = p.second;
            if (p.second.value > best_value) {
                best_value = p.second.value;
                best_mass = p.first;
            }
        }
    }

    // Reconstruct counts
    vector<long long> counts(cat_count, 0);
    long long cur_mass = best_mass;
    while (cur_mass > 0) {
        State& s = dp[cur_mass];
        int idx = s.prev_item;
        if (idx == -1) break;
        BinaryItem& it = binary_items[idx];
        counts[it.category] += it.copies;
        cur_mass = s.prev_mass;
    }

    // Output JSON
    cout << "{\n";
    for (int i = 0; i < cat_count; ++i) {
        cout << " \"" << categories[i] << "\": " << counts[i];
        if (i < cat_count - 1) cout << ",";
        cout << "\n";
    }
    cout << "}" << endl;

    return 0;
}
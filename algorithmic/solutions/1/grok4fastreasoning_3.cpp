#include <bits/stdc++.h>
using namespace std;

struct Item {
    string name;
    long long q, v, m, l;
};

struct State {
    long long value, mass, vol;
    int prev, x;
};

int main() {
    string all_input;
    string line;
    while (getline(cin, line)) {
        all_input += line;
    }
    string json;
    for (char c : all_input) {
        if (!isspace(static_cast<unsigned char>(c))) {
            json += c;
        }
    }
    vector<Item> items;
    map<string, vector<long long>> data;
    size_t pos = 0;
    if (json[pos] == '{') pos++;
    while (pos < json.size() && json[pos] != '}') {
        if (json[pos] != '"') { pos++; continue; }
        pos++;
        size_t start_key = pos;
        while (pos < json.size() && json[pos] != '"') pos++;
        string key = json.substr(start_key, pos - start_key);
        pos++;
        if (pos < json.size() && json[pos] == ':') pos++;
        if (pos < json.size() && json[pos] == '[') pos++;
        vector<long long> vals(4);
        for (int i = 0; i < 4; i++) {
            size_t start_num = pos;
            while (pos < json.size() && isdigit(json[pos])) pos++;
            string num_str = json.substr(start_num, pos - start_num);
            vals[i] = stoll(num_str);
            if (i < 3 && pos < json.size() && json[pos] == ',') pos++;
        }
        if (pos < json.size() && json[pos] == ']') pos++;
        data[key] = vals;
        if (pos < json.size() && json[pos] == ',') pos++;
    }
    for (auto& p : data) {
        Item it;
        it.name = p.first;
        it.q = p.second[0];
        it.v = p.second[1];
        it.m = p.second[2];
        it.l = p.second[3];
        items.push_back(it);
    }
    int n = items.size();
    long long M = 20000000LL;
    long long L = 25000000LL;
    // Compute order
    vector<pair<double, int>> order_dens(n);
    double alpha_order = 0.5;
    for (int i = 0; i < n; i++) {
        double norm_m = static_cast<double>(items[i].m) / M;
        double norm_l = static_cast<double>(items[i].l) / L;
        double cost = alpha_order * norm_m + (1.0 - alpha_order) * norm_l;
        double den = (cost > 0.0) ? static_cast<double>(items[i].v) / cost : 0.0;
        order_dens[i] = {-den, i};
    }
    sort(order_dens.begin(), order_dens.end());
    vector<Item> ordered_items(n);
    vector<int> orig_index(n);
    for (int i = 0; i < n; i++) {
        int idx = order_dens[i].second;
        ordered_items[i] = items[idx];
        orig_index[i] = idx;
    }
    // Beam search
    const int K = 1000;
    vector<vector<State>> layers(n + 1);
    layers[0].push_back({0, 0, 0, -1, 0});
    for (int t = 0; t < n; t++) {
        const auto& curr = layers[t];
        vector<State> candidates;
        for (size_t s = 0; s < curr.size(); s++) {
            const State& st = curr[s];
            long long rem_mass = M - st.mass;
            long long rem_vol = L - st.vol;
            const Item& it = ordered_items[t];
            long long x_max = it.q;
            if (it.m > 0) x_max = min(x_max, rem_mass / it.m);
            if (it.l > 0) x_max = min(x_max, rem_vol / it.l);
            for (long long x = 0; x <= x_max; x++) {
                long long new_mass = st.mass + x * it.m;
                long long new_vol = st.vol + x * it.l;
                long long new_value = st.value + x * it.v;
                if (new_mass <= M && new_vol <= L) {
                    candidates.push_back({new_value, new_mass, new_vol, static_cast<int>(s), static_cast<int>(x)});
                }
            }
        }
        // Sort: max value, then min mass, then min vol
        sort(candidates.begin(), candidates.end(), [](const State& a, const State& b) {
            if (a.value != b.value) return a.value > b.value;
            if (a.mass != b.mass) return a.mass < b.mass;
            return a.vol < b.vol;
        });
        int take = min(static_cast<int>(candidates.size()), K);
        layers[t + 1].clear();
        layers[t + 1].reserve(take);
        for (int i = 0; i < take; i++) {
            layers[t + 1].push_back(candidates[i]);
        }
    }
    // Reconstruct
    map<string, long long> output_map;
    if (!layers[n].empty()) {
        int current_layer = n;
        int current_idx = 0;
        vector<long long> ordered_counts(n, 0);
        for (int t = n - 1; t >= 0; t--) {
            const State& st = layers[current_layer][current_idx];
            ordered_counts[t] = st.x;
            current_idx = st.prev;
            current_layer--;
        }
        for (int t = 0; t < n; t++) {
            int orig = orig_index[t];
            output_map[items[orig].name] = ordered_counts[t];
        }
    }
    // Output
    cout << "{\n";
    bool first = true;
    for (const auto& p : output_map) {
        if (!first) cout << ",\n";
        first = false;
        cout << " \"" << p.first << "\": " << p.second;
    }
    cout << "\n}\n";
    return 0;
}
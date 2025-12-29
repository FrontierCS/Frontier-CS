#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>
#include <cctype>
#include <sstream>
#include <map>

using namespace std;

typedef long long ll;

struct Item {
    string name;
    ll q, v, m, l;
    ll cnt; // number taken
};

// Simple JSON parser for this specific format
bool parse_input(const string& json, vector<Item>& items, vector<string>& order) {
    items.clear();
    order.clear();
    size_t i = 0;
    // skip whitespace
    while (i < json.size() && isspace(json[i])) i++;
    if (i >= json.size() || json[i] != '{') return false;
    i++;
    while (i < json.size()) {
        // skip whitespace
        while (i < json.size() && isspace(json[i])) i++;
        if (i >= json.size()) return false;
        if (json[i] == '}') break;
        // parse key
        if (json[i] != '"') return false;
        i++;
        string key;
        while (i < json.size() && json[i] != '"') key += json[i++];
        if (i >= json.size() || json[i] != '"') return false;
        i++; // skip closing quote
        // skip to ':'
        while (i < json.size() && isspace(json[i])) i++;
        if (i >= json.size() || json[i] != ':') return false;
        i++;
        // skip whitespace
        while (i < json.size() && isspace(json[i])) i++;
        // expect '['
        if (i >= json.size() || json[i] != '[') return false;
        i++;
        // parse four integers
        vector<ll> nums;
        while (nums.size() < 4) {
            while (i < json.size() && isspace(json[i])) i++;
            if (i >= json.size()) return false;
            ll val = 0;
            bool neg = false;
            if (json[i] == '-') { neg = true; i++; }
            while (i < json.size() && isdigit(json[i])) {
                val = val * 10 + (json[i] - '0');
                i++;
            }
            if (neg) val = -val;
            nums.push_back(val);
            while (i < json.size() && isspace(json[i])) i++;
            if (nums.size() < 4) {
                if (i >= json.size() || json[i] != ',') return false;
                i++;
            }
        }
        // expect ']'
        while (i < json.size() && isspace(json[i])) i++;
        if (i >= json.size() || json[i] != ']') return false;
        i++;
        // skip to ',' or '}'
        while (i < json.size() && isspace(json[i])) i++;
        if (i < json.size() && json[i] == ',') i++;
        // store item
        items.push_back({key, nums[0], nums[1], nums[2], nums[3], 0});
        order.push_back(key);
    }
    return true;
}

int main() {
    // read entire input
    string json;
    char ch;
    while (cin.get(ch)) json += ch;

    vector<Item> items;
    vector<string> order;
    if (!parse_input(json, items, order)) {
        // should not happen with valid input
        return 1;
    }

    const ll M_MAX = 20000000; // mg
    const ll V_MAX = 25000000; // µL
    ll remaining_mass = M_MAX;
    ll remaining_volume = V_MAX;
    int n = items.size(); // should be 12

    // Greedy: one at a time, choose item with highest score based on remaining capacities
    while (true) {
        double best_score = -1;
        int best_idx = -1;
        for (int i = 0; i < n; i++) {
            if (items[i].cnt >= items[i].q) continue;
            if (items[i].m > remaining_mass || items[i].l > remaining_volume) continue;
            // score = value per unit of normalized resource consumption
            double score = items[i].v / (items[i].m / (double)remaining_mass + items[i].l / (double)remaining_volume);
            if (score > best_score) {
                best_score = score;
                best_idx = i;
            }
        }
        if (best_idx == -1) break;
        // take one
        items[best_idx].cnt++;
        remaining_mass -= items[best_idx].m;
        remaining_volume -= items[best_idx].l;
    }

    // Local improvement: try swaps and additions
    bool improved = true;
    while (improved) {
        improved = false;
        // Try to add an item without removing
        for (int j = 0; j < n; j++) {
            if (items[j].cnt >= items[j].q) continue;
            if (items[j].m <= remaining_mass && items[j].l <= remaining_volume) {
                items[j].cnt++;
                remaining_mass -= items[j].m;
                remaining_volume -= items[j].l;
                improved = true;
                break;
            }
        }
        if (improved) continue;
        // Try to swap one item for another (remove one i, add one j)
        for (int i = 0; i < n; i++) {
            if (items[i].cnt == 0) continue;
            for (int j = 0; j < n; j++) {
                if (i == j) continue;
                if (items[j].cnt >= items[j].q) continue;
                // Check if swapping increases value and is feasible
                if (items[j].v > items[i].v &&
                    remaining_mass + items[i].m >= items[j].m &&
                    remaining_volume + items[i].l >= items[j].l) {
                    // Perform swap
                    items[i].cnt--;
                    items[j].cnt++;
                    remaining_mass += items[i].m - items[j].m;
                    remaining_volume += items[i].l - items[j].l;
                    improved = true;
                    break;
                }
            }
            if (improved) break;
        }
    }

    // Output JSON in the original key order
    cout << "{";
    for (size_t idx = 0; idx < order.size(); idx++) {
        string key = order[idx];
        // find item with that name
        for (const auto& it : items) {
            if (it.name == key) {
                cout << "\"" << key << "\": " << it.cnt;
                break;
            }
        }
        if (idx != order.size() - 1) cout << ",";
    }
    cout << "}" << endl;

    return 0;
}
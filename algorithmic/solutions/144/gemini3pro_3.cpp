#include <iostream>
#include <vector>
#include <algorithm>
#include <set>

using namespace std;

int n;
int val_o1, val_o2;

// Global state
vector<int> up_candidates;
vector<int> down_candidates;
vector<int> unknown_candidates;
vector<pair<int, int>> balancing_pairs;
vector<int> s_active;

// Query function
pair<int, int> query(const vector<int>& indices) {
    cout << "0 " << indices.size();
    for (int x : indices) cout << " " << x;
    cout << endl;
    int m1, m2;
    cin >> m1 >> m2;
    return {m1, m2};
}

// Helper to get query set from all available indices excluding u and v
// The full set (s_active + balancing_pairs) is always balanced with medians O1, O2.
vector<int> get_query_indices_excluding(int u, int v) {
    vector<int> q;
    for (int x : s_active) {
        if (x != u && x != v) q.push_back(x);
    }
    for (auto& p : balancing_pairs) {
        if (p.first != u && p.first != v) q.push_back(p.first);
        if (p.second != u && p.second != v) q.push_back(p.second);
    }
    return q;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n;
    val_o1 = n / 2;
    val_o2 = n / 2 + 1;

    for (int i = 1; i <= n; ++i) {
        unknown_candidates.push_back(i);
        s_active.push_back(i);
    }

    int o1 = -1, o2 = -1;

    while (o1 == -1 || o2 == -1) {
        // If s_active reduced to 2, they must be the targets
        if (s_active.size() == 2) {
            int u = s_active[0];
            int v = s_active[1];
            // Resolve u vs v
            int w = -1;
            if (!balancing_pairs.empty()) w = balancing_pairs[0].second; // Use a known L
            else {
                // Should not happen for N>=6 if we reduced size. 
                // If N is small but we didn't remove anything, size wouldn't be 2.
                // Just output arbitrarily if we can't distinguish.
                cout << "1 " << u << " " << v << endl;
                return 0;
            }

            pair<int, int> res = query(get_query_indices_excluding(u, w));
            // w is L.
            // If u=O1: {O1, L} removed -> Partial Down (medians < O1, = O2)
            // If u=O2: {O2, L} removed -> Shift Down (medians < O1, = O1)
            if (res.first < val_o1 && res.second == val_o2) {
                o1 = u; o2 = v;
            } else {
                o1 = v; o2 = u;
            }
            break;
        }

        int u = -1, v = -1;
        
        // Selection Strategy
        if (o1 == -1 && o2 == -1 && !up_candidates.empty() && !down_candidates.empty()) {
            u = up_candidates.back(); up_candidates.pop_back();
            v = down_candidates.back(); down_candidates.pop_back();
        }
        else if (o1 != -1 && !down_candidates.empty()) {
             u = o1; 
             v = down_candidates.back(); down_candidates.pop_back();
        }
        else if (o2 != -1 && !up_candidates.empty()) {
             v = o2; 
             u = up_candidates.back(); up_candidates.pop_back();
        }
        else if (!unknown_candidates.empty()) {
            u = unknown_candidates.back(); unknown_candidates.pop_back();
            if (o1 != -1) {
                v = u; u = o1;
            } else if (o2 != -1) {
                v = o2;
            } else {
                if (!unknown_candidates.empty()) {
                    v = unknown_candidates.back(); unknown_candidates.pop_back();
                } else if (!up_candidates.empty()) {
                    v = up_candidates.back(); up_candidates.pop_back();
                } else if (!down_candidates.empty()) {
                    v = down_candidates.back(); down_candidates.pop_back();
                }
            }
        } else {
            // Should be handled by size==2 check, but break to be safe
            break;
        }

        pair<int, int> res = query(get_query_indices_excluding(u, v));
        int m1 = res.first;
        int m2 = res.second;

        // Special handling if we used a known target
        if (u == o1) { 
            // Pair {O1, v}. v is candidate (Down or Unknown).
            if (m1 < val_o1 && m2 > val_o2) { // Spread: {O1, O2}
                o2 = v;
            } 
            // Else v is L or S, discard.
            continue; 
        }
        if (v == o2) {
             // Pair {u, O2}. u is candidate (Up or Unknown).
             if (m1 < val_o1 && m2 > val_o2) { // Spread: {O1, O2}
                 o1 = u;
             }
             // Else u is S or L, discard.
             continue;
        }

        // Standard logic for candidates u, v
        if (m1 == val_o1 && m2 == val_o2) { // Stable: {S, L}
            // Remove from s_active permanently
            vector<int> next_s;
            for(int x : s_active) if(x != u && x != v) next_s.push_back(x);
            s_active = next_s;
            balancing_pairs.push_back({u, v}); // Store for balance padding
        }
        else if (m1 == val_o2 && m2 > val_o2) { // Shift Up: {S, S} or {S, O1}
            up_candidates.push_back(u);
            up_candidates.push_back(v);
        }
        else if (m1 < val_o1 && m2 == val_o1) { // Shift Down: {L, L} or {L, O2}
            down_candidates.push_back(u);
            down_candidates.push_back(v);
        }
        else if (m1 == val_o1 && m2 > val_o2) { // Partial Up: {S, O2}
            // One is O2. Resolve with a known L if possible.
            int w = -1;
            if (!balancing_pairs.empty()) w = balancing_pairs[0].second; // L
            else { for(int x : s_active) if(x!=u && x!=v) { w = x; break; } }
            
            pair<int, int> res2 = query(get_query_indices_excluding(u, w));
            
            int target_o2 = -1;
            if (!balancing_pairs.empty()) {
                // w is L
                if (res2.first == val_o1 && res2.second == val_o2) { // Stable -> u=S
                    target_o2 = v;
                } else { // Shift Down -> u=O2
                    target_o2 = u;
                }
            } else {
                // w is unknown S/L
                if (res2.first == val_o2 && res2.second > val_o2) target_o2 = v; // Up -> u=S
                else if (res2.first == val_o1 && res2.second == val_o2) target_o2 = v; // Stable -> u=S
                else target_o2 = u;
            }
            o2 = target_o2;
        }
        else if (m1 < val_o1 && m2 == val_o2) { // Partial Down: {L, O1}
            // One is O1. Resolve.
            int w = -1;
            if (!balancing_pairs.empty()) w = balancing_pairs[0].first; // S
            else { for(int x : s_active) if(x!=u && x!=v) { w = x; break; } }
            
            pair<int, int> res2 = query(get_query_indices_excluding(u, w));
            int target_o1 = -1;
            // w is S (or unknown)
            // if w is S: u=L -> Stable. u=O1 -> Shift Up.
            if (!balancing_pairs.empty()) {
                if (res2.first == val_o1 && res2.second == val_o2) target_o1 = v; // Stable -> u=L
                else target_o1 = u; // Shift Up -> u=O1
            } else {
                if (res2.first == val_o1 && res2.second == val_o2) target_o1 = v;
                else if (res2.first < val_o1 && res2.second == val_o1) target_o1 = v; // Down -> u=L
                else target_o1 = u;
            }
            o1 = target_o1;
        }
        else if (m1 < val_o1 && m2 > val_o2) { // Spread: {O1, O2}
            // Distinguish O1 vs O2
            int w = -1;
            if (!balancing_pairs.empty()) w = balancing_pairs[0].second; // L
            else { for(int x : s_active) if(x!=u && x!=v) { w = x; break; } }
            
            pair<int, int> res2 = query(get_query_indices_excluding(u, w));
            // w is L. u=O1 -> Partial Down. u=O2 -> Shift Down.
            if (res2.first < val_o1 && res2.second == val_o2) {
                o1 = u; o2 = v;
            } else {
                o1 = v; o2 = u;
            }
        }
    }

    cout << "1 " << o1 << " " << o2 << endl;

    return 0;
}
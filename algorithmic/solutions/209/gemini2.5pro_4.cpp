#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <map>
#include <algorithm>
#include <set>

using namespace std;

long long query(int u, int d) {
    cout << "? " << u << " " << d << endl;
    long long response;
    cin >> response;
    return response;
}

void solve() {
    int h;
    cin >> h;
    int n = (1 << h) - 1;

    map<long long, int> counts;
    for (int i = 1; i <= n; ++i) {
        long long res = query(i, 1);
        counts[res]++;
    }

    if (h == 2) {
        long long root_children_sum = -1, root_weight = -1;
        for (auto const& [val, num] : counts) {
            if (num == 1) {
                root_children_sum = val;
            } else { // num == 2
                root_weight = val;
            }
        }
        cout << "! " << root_children_sum + root_weight << endl;
        return;
    }
    
    // Sums of weights in subtrees rooted at the current level being processed
    vector<long long> current_subtree_sums;

    // weights of nodes at level d = level_h - 1
    map<long long, int> leaf_parent_weights;
    for (auto const& [val, num] : counts) {
        if (num == 2) {
            leaf_parent_weights[val]++;
        }
    }
    
    // Remove weights of leaf parents from counts
    for(auto const& [w, num] : leaf_parent_weights){
        counts[w] -= 2*num;
        if(counts[w] == 0) counts.erase(w);
    }
    
    // For each node v at depth h-2, we have its weight W(v).
    // The query for v is R(v) = W(v/2) + S(v).
    // Total sum in v's subtree is Sum(v) = W(v) + S(v).
    // So, Sum(v) = W(v) + R(v) - W(v/2).
    // We don't know which R(v) and W(v/2) corresponds to which W(v).
    // But we know that for each W(v) there must be some R(v) > W(v).
    // We can assume the smallest valid R(v) corresponds to it.
    for (auto const& [w, num] : leaf_parent_weights) {
        for (int i = 0; i < num; ++i) {
            auto it = counts.upper_bound(w);
            long long r = it->first;
            counts[r]--;
            if (counts[r] == 0) {
                counts.erase(r);
            }
            // We have identified Sum(v) + W(v/2) = r and W(v)=w.
            // Let's store r for now. This is sum in child subtrees + weight of parent + weight of grandparent.
            // A better invariant is sum of weights in subtree + weight of parent.
            // S_v_full = W(v)+S(v). R_v = W(v/2)+S(v).
            // S_v_full + W(v/2) = W(v) + R(v).
            // Let's track S_v_full values.
            current_subtree_sums.push_back(r);
        }
    }

    // Now iterate upwards from level h-3 to 0
    for (int level = h - 3; level >= 0; --level) {
        if (current_subtree_sums.empty()) break;
        
        sort(current_subtree_sums.rbegin(), current_subtree_sums.rend());
        
        vector<long long> next_subtree_sums;
        
        map<long long, int> parent_weights;

        while(current_subtree_sums.size() >= 2){
            long long s1 = current_subtree_sums.back();
            current_subtree_sums.pop_back();
            long long s2 = current_subtree_sums.back();
            current_subtree_sums.pop_back();

            long long combined_sum = s1 + s2;
            auto it = counts.upper_bound(combined_sum);
            long long r = it->first;
            counts[r]--;
            if (counts[r] == 0) {
                counts.erase(r);
            }
            next_subtree_sums.push_back(r);
        }
        
        current_subtree_sums = next_subtree_sums;
    }

    long long total_sum = 0;
    if(!current_subtree_sums.empty()){
        total_sum = current_subtree_sums[0];
    } else { // Should not happen for h > 2
         for(auto const& [val, num] : counts){
             if(num > 0) total_sum = val;
         }
    }


    cout << "! " << total_sum << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}
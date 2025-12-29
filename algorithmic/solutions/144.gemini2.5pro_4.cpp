#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <cassert>

using namespace std;

// Function to make a query and get medians
pair<int, int> query(const vector<int>& indices) {
    cout << "0 " << indices.size();
    for (int idx : indices) {
        cout << " " << idx;
    }
    cout << endl;
    int m1, m2;
    cin >> m1 >> m2;
    return {m1, m2};
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    // Phase 1: Partition using 1, 2, 3 as base
    map<pair<int, int>, vector<int>> groups;
    map<int, int> val_counts;
    vector<pair<int, int>> l_medians(n + 1);

    for (int l = 4; l <= n; ++l) {
        pair<int, int> med = query({1, 2, 3, l});
        if (med.first > med.second) swap(med.first, med.second);
        groups[med].push_back(l);
        val_counts[med.first]++;
        val_counts[med.second]++;
        l_medians[l] = med;
    }

    // Phase 2: Identify v_a, v_b, v_c and group sizes
    int v_b = -1;
    int max_freq = 0;
    for (auto const& [val, freq] : val_counts) {
        if (freq > max_freq) {
            max_freq = freq;
            v_b = val;
        }
    }

    pair<int, int> p_ab = {-1, -1}, p_bc = {-1, -1};
    vector<pair<int, pair<int,int>>> group_sizes;
    for(auto const& [pair, members] : groups) {
        group_sizes.push_back({members.size(), pair});
    }
    sort(group_sizes.rbegin(), group_sizes.rend());

    for(const auto& gs : group_sizes) {
        if (gs.second.first == v_b || gs.second.second == v_b) {
            if (p_ab.first == -1) p_ab = gs.second;
            else {
                p_bc = gs.second;
                break;
            }
        }
    }

    int v_a = (p_ab.first == v_b) ? p_ab.second : p_ab.first;
    int v_c = (p_bc.first == v_b) ? p_bc.second : p_bc.first;
    if (v_a > v_c) swap(v_a, v_c);
    
    vector<int> G1, G2, G3, G4;
    if(groups.count({v_a, v_b})) G1 = groups[{v_a, v_b}];
    if(groups.count({v_b, v_c})) G4 = groups[{v_b, v_c}];

    for (int l = 4; l <= n; ++l) {
        pair<int, int> med = l_medians[l];
        if ((med.first == v_a && med.second == v_b) || (med.first == v_b && med.second == v_c)) {
            continue;
        }
        int p_l = (med.first == v_b) ? med.second : med.first;
        if (p_l < v_b) {
            G2.push_back(l);
        } else {
            G3.push_back(l);
        }
    }

    int s1 = G1.size();
    int s2 = G2.size();
    int s3 = G3.size();

    int r_a = s1 + 1;
    int r_b = s1 + s2 + 2;
    int r_c = s1 + s2 + s3 + 3;

    // Phase 3: Setup for selection
    if (G1.size() < 2 || G4.empty()) {
        // Fallback for edge cases where pivots are not easily available.
        // Query the whole set, get median values, then brute force pairs.
        pair<int, int> med_all = query({1,2,3,4,5,6});
        for (int i = 1; i <= n; ++i) {
            for (int j = i + 1; j <= n; ++j) {
                vector<int> q_indices;
                q_indices.push_back(i);
                q_indices.push_back(j);
                for(int k=1; k<=n && q_indices.size() < 6; ++k) {
                    if (k != i && k != j) q_indices.push_back(k);
                }
                pair<int, int> med_pair = query(q_indices);
                if ((med_pair.first == med_all.first && med_pair.second == med_all.second) ||
                    (med_pair.first == med_all.second && med_pair.second == med_all.first)) {
                    // Not a guarantee, but a strong heuristic
                }
            }
        }
        // As a simple robust fallback, just sort all elements.
        vector<int> all_indices;
        for(int i=1; i<=n; ++i) all_indices.push_back(i);
        int p1=1, p2=2, p3=3, p4=4;
        auto simple_comp = [&](int u, int v) {
            pair<int,int> med = query({u,v,p1,p4});
            pair<int,int> med_u = query({u,p1,p2,p3});
            pair<int,int> med_v = query({v,p1,p2,p3});
            return med_u.second < med_v.second;
        };
        sort(all_indices.begin(), all_indices.end(), simple_comp);
        cout << "1 " << all_indices[n/2-1] << " " << all_indices[n/2] << endl;
        return 0;
    }

    int piv1 = G1[0], piv2 = G1[1], o1 = G4[0];
    auto is_less = [&](int u, int v) {
        pair<int, int> med_u = query({u, piv1, piv2, o1});
        pair<int, int> med_v = query({v, piv1, piv2, o1});
        int p_p2;
        if (med_u.first == med_v.first || med_u.first == med_v.second) p_p2 = med_u.first;
        else p_p2 = med_u.second;
        int p_u = (med_u.first == p_p2) ? med_u.second : med_u.first;
        int p_v = (med_v.first == p_p2) ? med_v.second : med_v.first;
        return p_u < p_v;
    };
    
    vector<int> temp_123 = {1, 2, 3};
    sort(temp_123.begin(), temp_123.end(), is_less);
    int idx_a = temp_123[0], idx_b = temp_123[1], idx_c = temp_123[2];
    
    int R1 = n / 2, R2 = n / 2 + 1;
    int ans1 = -1, ans2 = -1;

    // Phase 4: Case analysis and selection
    if (r_b == R1) {
        ans1 = idx_b;
        vector<int> C = G3; C.push_back(idx_c);
        nth_element(C.begin(), C.begin(), C.end(), is_less);
        ans2 = C.front();
    } else if (r_b == R2) {
        ans2 = idx_b;
        vector<int> C = G2; C.push_back(idx_a);
        nth_element(C.begin(), C.end()-1, C.end(), is_less);
        ans1 = C.back();
    } else if (r_a < R1 && r_b > R2) { // both in G2
        vector<int> C = G2; C.push_back(idx_a);
        int target1 = R1 - r_a;
        int target2 = R2 - r_a;
        nth_element(C.begin(), C.begin() + target1 - 1, C.end(), is_less);
        ans1 = C[target1 - 1];
        nth_element(C.begin() + target1, C.begin() + target2 - 1, C.end(), is_less);
        ans2 = C[target2 - 1];
    } else if (r_b < R1 && r_c > R2) { // both in G3
        vector<int> C = G3; C.push_back(idx_b);
        int target1 = R1 - r_b;
        int target2 = R2 - r_b;
        nth_element(C.begin(), C.begin() + target1 - 1, C.end(), is_less);
        ans1 = C[target1 - 1];
        nth_element(C.begin() + target1, C.begin() + target2 - 1, C.end(), is_less);
        ans2 = C[target2 - 1];
    } else { // split between G2 and G3
        vector<int> C1 = G2; C1.push_back(idx_a);
        nth_element(C1.begin(), C1.end() - 1, C1.end(), is_less);
        ans1 = C1.back();
        vector<int> C2 = G3; C2.push_back(idx_b);
        nth_element(C2.begin(), C2.begin(), C2.end(), is_less);
        ans2 = C2.front();
    }

    cout << "1 " << ans1 << " " << ans2 << endl;

    return 0;
}
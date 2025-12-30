#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <set>

using namespace std;

// Memoization for queries to avoid re-querying the same set of indices
map<vector<int>, pair<int, int>> memo;

// Function to perform a query and get the two medians
pair<int, int> do_query(vector<int> indices) {
    sort(indices.begin(), indices.end());
    if (memo.count(indices)) {
        return memo[indices];
    }

    cout << "0 " << indices.size();
    for (int idx : indices) {
        cout << " " << idx;
    }
    cout << endl;
    
    int m1, m2;
    cin >> m1 >> m2;
    if (m1 > m2) swap(m1, m2);
    return memo[indices] = {m1, m2};
}

// Finds the index of the median value among p[i], p[j], p[k]
int get_median_of_3(int i, int j, int k, const vector<int>& all_indices) {
    // Find helper indices that are not i, j, or k
    int o1 = -1, o2 = -1, o3 = -1;
    for (int other : all_indices) {
        if (other != i && other != j && other != k) {
            if (o1 == -1) o1 = other;
            else if (o2 == -1) o2 = other;
            else {
                o3 = other;
                break;
            }
        }
    }

    // Query with two different helpers to find the median value
    pair<int, int> res1 = do_query({i, j, k, o1});
    pair<int, int> res2 = do_query({i, j, k, o2});

    set<int> s1 = {res1.first, res1.second};
    set<int> s2 = {res2.first, res2.second};
    vector<int> intersection;
    set_intersection(s1.begin(), s1.end(), s2.begin(), s2.end(), back_inserter(intersection));

    int med_val;
    if (intersection.size() == 1) {
        med_val = intersection[0];
    } else { // intersection size is 2, need a third query
        pair<int, int> res3 = do_query({i, j, k, o3});
        if (res3.first == intersection[0] || res3.second == intersection[0]) {
            med_val = intersection[0];
        } else {
            med_val = intersection[1];
        }
    }
    
    // Determine which index (i, j, or k) corresponds to med_val
    pair<int, int> m_jk = do_query({j, k, o1, o2});
    if (med_val != m_jk.first && med_val != m_jk.second) {
        return i;
    }

    pair<int, int> m_ik = do_query({i, k, o1, o2});
    if (med_val != m_ik.first && med_val != m_ik.second) {
        return j;
    }

    return k;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    vector<int> candidates(n);
    iota(candidates.begin(), candidates.end(), 1);

    vector<int> all_indices = candidates;

    while (candidates.size() > 2) {
        vector<int> group;
        // Take first 4 elements as a group for elimination
        for(int i=0; i<4; ++i) group.push_back(candidates[i]);
        
        map<int, int> med_counts;
        for(int cand : group) med_counts[cand] = 0;
        
        int med_012 = get_median_of_3(group[0], group[1], group[2], all_indices);
        int med_013 = get_median_of_3(group[0], group[1], group[3], all_indices);
        int med_023 = get_median_of_3(group[0], group[2], group[3], all_indices);
        int med_123 = get_median_of_3(group[1], group[2], group[3], all_indices);

        med_counts[med_012]++;
        med_counts[med_013]++;
        med_counts[med_023]++;
        med_counts[med_123]++;

        vector<int> to_remove;
        for (auto const& [idx, count] : med_counts) {
            if (count == 0) {
                to_remove.push_back(idx);
            }
        }
        
        vector<int> next_candidates;
        for(int c: candidates) {
            bool should_remove = false;
            for(int rem : to_remove) {
                if (c == rem) {
                    should_remove = true;
                    break;
                }
            }
            if (!should_remove) {
                next_candidates.push_back(c);
            }
        }
        candidates = next_candidates;
    }

    cout << "1 " << candidates[0] << " " << candidates[1] << endl;

    return 0;
}
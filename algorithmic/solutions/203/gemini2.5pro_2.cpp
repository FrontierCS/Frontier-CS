#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <string>

using namespace std;

// Helper function to make a query to the judge
int query(const vector<int>& chameleons) {
    if (chameleons.empty()) {
        return 0;
    }
    cout << "Query " << chameleons.size();
    for (int c : chameleons) {
        cout << " " << c;
    }
    cout << endl;
    int result;
    cin >> result;
    return result;
}

// Helper to concatenate vectors or a vector and an element
template <typename T>
vector<T> concat(const vector<T>& a, const vector<T>& b) {
    vector<T> res = a;
    res.insert(res.end(), b.begin(), b.end());
    return res;
}

template <typename T>
vector<T> concat(const vector<T>& a, const T& b) {
    vector<T> res = a;
    res.push_back(b);
    return res;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int N;
    cin >> N;

    // Step 1: Partition chameleons into two gender groups, X and Y.
    vector<int> group_X, group_Y;
    vector<bool> classified(2 * N + 1, false);

    group_X.push_back(1);
    classified[1] = true;

    int y_ref = -1;
    for (int i = 2; i <= 2 * N; ++i) {
        if (query({1, i}) == 1) {
            y_ref = i;
            break;
        }
    }
    group_Y.push_back(y_ref);
    classified[y_ref] = true;
    
    vector<int> unclassified;
    for(int i = 2; i <= 2 * N; ++i) {
        if (!classified[i]) {
            unclassified.push_back(i);
        }
    }

    while (group_X.size() < N || group_Y.size() < N) {
        vector<int> next_unclassified;
        for (int k : unclassified) {
            int res_y = query(concat(group_Y, k));
            if (res_y == (int)group_Y.size()) {
                group_X.push_back(k);
            } else {
                int res_x = query(concat(group_X, k));
                if (res_x == (int)group_X.size()) {
                    group_Y.push_back(k);
                } else {
                    next_unclassified.push_back(k);
                }
            }
        }
        unclassified = next_unclassified;
    }

    // Step 2: Find the twin for each chameleon in one group.
    vector<pair<int, int>> pairs;
    vector<bool> paired(2 * N + 1, false);

    for (int x : group_X) {
        vector<int> y_candidates;
        for (int y : group_Y) {
            if (!paired[y]) {
                y_candidates.push_back(y);
            }
        }

        vector<int> p_chameleons;
        for (const auto& p : pairs) {
            p_chameleons.push_back(p.first);
            p_chameleons.push_back(p.second);
        }

        int l = 0, r = y_candidates.size() - 1;
        int twin_y = -1;

        while (l <= r) {
            if (l == r) {
                twin_y = y_candidates[l];
                break;
            }
            int mid = l + (r - l) / 2;
            vector<int> y_subset;
            for (int i = l; i <= mid; ++i) {
                y_subset.push_back(y_candidates[i]);
            }
            
            vector<int> current_query_set = p_chameleons;
            current_query_set.push_back(x);
            current_query_set.insert(current_query_set.end(), y_subset.begin(), y_subset.end());

            // A chameleon and its twin have the same color. If the twin of x is in y_subset,
            // the number of distinct colors will be one less than if all colors were unique.
            // Love relationships can also cause color count reduction.
            // This finds a "related" chameleon, which we assume is the twin.
            if (query(current_query_set) < (int)pairs.size() + 1 + (int)y_subset.size()) {
                r = mid;
            } else {
                l = mid + 1;
            }
        }
        
        pairs.push_back({x, twin_y});
        paired[x] = true;
        paired[twin_y] = true;
    }

    // Step 3: Output the pairs.
    for (const auto& p : pairs) {
        cout << "Answer " << p.first << " " << p.second << endl;
    }

    return 0;
}
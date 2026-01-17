#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

// Function to send a query to the judge
int query(const vector<int>& c) {
    if (c.empty()) {
        return 0;
    }
    cout << "Query " << c.size();
    for (int x : c) {
        cout << " " << x;
    }
    cout << endl;
    int result;
    cin >> result;
    if (result == -1) exit(0); // Exit on error
    return result;
}

// A chameleon p has partners in a group if a query with p and the group
// results in fewer distinct colors than the sum of their individual queries.
// Specifically, for a same-gender group S, Query(S)=|S|. If we add an opposite-gender
// chameleon p, Query(S u {p}) will be |S|+1 if p has no connections (color-twin,
// lover, or loved by) in S. If it has any connection, the result will be <= |S|.
// This function returns the number of such connections.
int count_partners(int p, const vector<int>& group) {
    if (group.empty()) return 0;
    vector<int> q_group = group;
    q_group.push_back(p);
    return (int)group.size() + 1 - query(q_group);
}

// Recursively find all partners of p in a given group.
// This uses a divide and conquer approach.
void find_partners_recursive(int p, const vector<int>& group, vector<int>& partners) {
    if (group.empty()) {
        return;
    }
    // Check if any partners exist in the current group segment
    int num_total = count_partners(p, group);
    if (num_total == 0) {
        return;
    }
    if (group.size() == 1) {
        partners.push_back(group[0]);
        return;
    }

    int mid = group.size() / 2;
    vector<int> left(group.begin(), group.begin() + mid);
    vector<int> right(group.begin() + mid, group.end());
    
    // Count partners in the left half to decide which subproblems to solve
    int num_left = count_partners(p, left);
    if (num_left > 0) {
        find_partners_recursive(p, left, partners);
    }
    if (num_total - num_left > 0) {
        find_partners_recursive(p, right, partners);
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int N;
    cin >> N;

    // Phase 1: Partition chameleons into two gender groups
    vector<int> group1, group2;
    group1.push_back(1);

    for (int i = 2; i <= 2 * N; ++i) {
        if (group1.size() < N) {
            vector<int> test_group = group1;
            test_group.push_back(i);
            // If adding 'i' to a same-gender group doesn't create color/love links,
            // the number of colors increases by one.
            if (query(test_group) == (int)group1.size() + 1) {
                group1.push_back(i);
            } else {
                group2.push_back(i);
            }
        } else {
            group2.push_back(i);
        }
    }
    
    // Ensure group1 has size N, move from group2 if needed
    while (group1.size() < N) {
        group1.push_back(group2.back());
        group2.pop_back();
    }
     while (group2.size() < N) {
        group2.push_back(group1.back());
        group1.pop_back();
    }


    // Phase 2: Build the 'partner' graph.
    // A chameleon y is a 'partner' of x if Query({x, y}) would result in 1.
    // This includes color-twins and non-mutual love pairs.
    vector<vector<int>> partners_of(2 * N + 1);
    
    for (int p : group1) {
        find_partners_recursive(p, group2, partners_of[p]);
    }
    for (int p : group2) {
        find_partners_recursive(p, group1, partners_of[p]);
    }

    // Phase 3: Identify color-twin pairs.
    // The color-twin relationship (x, c_x) is symmetric. The partner relation
    // from `y = loves(x)` is not necessarily symmetric in the partner graph.
    // A pair (x,y) is a color-twin pair if y is a partner of x AND x is a partner of y.
    // Love-pairs `x loves y` (`y=l_x`) implies `x` is loved by `y` (`x=p_y`).
    // This is also symmetric in our partner definition.
    // We can distinguish them: Query({x,y})=1 for color-twins, but Query({x,y})=2 for mutual-love.
    // Our partner finding method implicitly filters out mutual love pairs.
    // The key insight is that `y = p_x` (y loves x) is not symmetric in the `loves` graph,
    // so `x` is not necessarily `p_y`. Only color-twin relationship `y=c_x` is truly symmetric.
    vector<bool> paired(2 * N + 1, false);
    for (int i = 1; i <= 2 * N; ++i) {
        if (paired[i]) continue;
        for (int partner : partners_of[i]) {
            if (paired[partner]) continue;
            
            bool is_symmetric_partner = false;
            for (int p_of_p : partners_of[partner]) {
                if (p_of_p == i) {
                    is_symmetric_partner = true;
                    break;
                }
            }
            
            // If `(i, partner)` is a color-twin pair, `i` will be a partner of `partner`.
            // If it's a love-pair `partner loves i`, `i` is not necessarily a partner of `partner`.
            if (is_symmetric_partner) {
                cout << "Answer " << i << " " << partner << endl;
                paired[i] = true;
                paired[partner] = true;
                break;
            }
        }
    }

    return 0;
}
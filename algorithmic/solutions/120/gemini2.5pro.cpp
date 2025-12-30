#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

// Use a map to cache query results to avoid re-querying.
map<vector<int>, int> memo;

int ask(int a, int b, int c) {
    if (a > b) swap(a, b);
    if (b > c) swap(b, c);
    if (a > b) swap(a, b);
    
    vector<int> key = {a, b, c};
    if (memo.count(key)) {
        return memo[key];
    }
    cout << "? " << a << " " << b << " " << c << endl;
    int response;
    cin >> response;
    return memo[key] = response;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n = 100;
    vector<vector<int>> adj(n + 1, vector<int>(n + 1, 0));
    vector<int> p(n + 1); // p[i] = E(1, i)

    // Step 1: Determine all p[i] = E(1, i)
    // We can find p[i]+p[j]+p[k] for any i,j,k > 1.
    auto get_p_sum = [&](int i, int j, int k) {
        long long q1ij = ask(1, i, j);
        long long q1ik = ask(1, i, k);
        long long q1jk = ask(1, j, k);
        long long qijk = ask(i, j, k);
        return (q1ij + q1ik + q1jk - qijk) / 2;
    };

    int s234 = get_p_sum(2, 3, 4);
    vector<int> p_rel(n + 1); // p_rel[i] stores if p[i] is same as p[2]

    p_rel[2] = 0; // p[2] = p[2]
    int s235 = get_p_sum(2, 3, 5);
    int p4_minus_p5 = s234 - s235;
    if (p4_minus_p5 == 0) {
       // p[4] == p[5]
    } else {
       // p[4] != p[5]
    }

    // Determine p[i] relative to p[2]
    // p[i] - p[2] = (p[i]+p[3]+p[4]) - (p[2]+p[3]+p[4])
    for (int i = 3; i <= n; ++i) {
        int s_i34 = get_p_sum(i, 3, 4);
        int p_i_minus_p2 = s_i34 - s234;
        if (p_i_minus_p2 == 0) {
            p_rel[i] = 0; // p[i] == p[2]
        } else {
            p_rel[i] = 1; // p[i] != p[2]
        }
    }
    
    // Determine the absolute value of p[2]
    int p2_val = 0;
    int p3_val = p_rel[3] ? 1-p2_val : p2_val;
    int p4_val = p_rel[4] ? 1-p2_val : p2_val;

    if (p2_val + p3_val + p4_val != s234) {
        p2_val = 1;
    }
    
    // Set absolute values
    p[2] = p2_val;
    for (int i = 3; i <= n; ++i) {
        if (p_rel[i] == 0) {
            p[i] = p[2];
        } else {
            p[i] = 1 - p[2];
        }
    }

    // Step 2: Fill the adjacency matrix
    for (int i = 2; i <= n; ++i) {
        adj[1][i] = adj[i][1] = p[i];
    }

    for (int i = 2; i <= n; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            int q1ij = ask(1, i, j);
            adj[i][j] = adj[j][i] = q1ij - p[i] - p[j];
        }
    }

    // Step 3: Output the result
    cout << "!" << endl;
    for (int i = 1; i <= n; ++i) {
        string row = "";
        for (int j = 1; j <= n; ++j) {
            row += to_string(adj[i][j]);
        }
        cout << row << endl;
    }

    return 0;
}
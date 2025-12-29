#include <bits/stdc++.h>
using namespace std;

int n;
vector<int> ask(int x, int y, int z) {
    cout << "? " << x << " " << y << " " << z << endl;
    cout.flush();
    int r;
    cin >> r;
    vector<int> res;
    for (int i = 0; i < r; ++i) {
        int a, b;
        cin >> a >> b;
        res.push_back(a);
        res.push_back(b);
    }
    return res;
}

bool contains_pair(const vector<int>& flat, int u, int v) {
    for (size_t i = 0; i < flat.size(); i += 2) {
        int a = flat[i], b = flat[i+1];
        if ((a == u && b == v) || (a == v && b == u))
            return true;
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int k;
    cin >> k >> n;
    const int R = 0;
    const int T = 20;

    vector<int> cnt(n, 0);
    // Estimate distances from R by sampling
    for (int i = 1; i < n; ++i) {
        for (int t = 0; t < T; ++t) {
            int j = (i + t * 123) % n;
            while (j == R || j == i) j = (j + 1) % n;
            vector<int> res = ask(R, i, j);
            if (contains_pair(res, R, i))
                cnt[i]++;
        }
    }

    // Order doors by estimated closeness to R
    vector<int> order;
    order.push_back(R);
    vector<int> others;
    for (int i = 1; i < n; ++i) others.push_back(i);
    sort(others.begin(), others.end(), [&](int a, int b) {
        return cnt[a] > cnt[b];
    });
    for (int x : others) order.push_back(x);

    vector<bool> used(n, false);
    used[R] = true;
    vector<int> right, left;
    right.push_back(R);
    left.push_back(R);

    // First neighbor (right side)
    int a1 = order[1];
    used[a1] = true;
    right.push_back(a1);
    int right_end = a1;

    // Find the other neighbor (left side)
    int other_neighbor = -1;
    for (int idx = 2; idx < n; ++idx) {
        int cand = order[idx];
        vector<int> res = ask(R, a1, cand);
        if (res.size() == 4) { // two pairs
            bool both_contain_R = true;
            for (size_t i = 0; i < 4; i += 2) {
                int u = res[i], v = res[i+1];
                if (u != R && v != R) {
                    both_contain_R = false;
                    break;
                }
            }
            if (both_contain_R) {
                other_neighbor = cand;
                used[other_neighbor] = true;
                left.push_back(other_neighbor);
                break;
            }
        }
    }
    if (other_neighbor == -1) {
        // Fallback: assume the second in order is the other neighbor
        other_neighbor = order[2];
        used[other_neighbor] = true;
        left.push_back(other_neighbor);
    }
    int left_end = other_neighbor;

    // Process remaining doors
    for (int idx = 2; idx < n; ++idx) {
        int X = order[idx];
        if (used[X]) continue;

        // Check adjacency to current ends
        vector<int> res_right = ask(R, right_end, X);
        bool adj_right = contains_pair(res_right, right_end, X);
        vector<int> res_left = ask(R, left_end, X);
        bool adj_left = contains_pair(res_left, left_end, X);

        if (adj_right && !adj_left) {
            right.push_back(X);
            right_end = X;
            used[X] = true;
        } else if (adj_left && !adj_right) {
            left.push_back(X);
            left_end = X;
            used[X] = true;
        } else if (adj_right && adj_left) {
            // Ambiguous: likely the door opposite R
            // Decide with an extra query
            vector<int> res_mid = ask(right_end, left_end, X);
            if (contains_pair(res_mid, right_end, X)) {
                right.push_back(X);
                right_end = X;
                used[X] = true;
            } else if (contains_pair(res_mid, left_end, X)) {
                left.push_back(X);
                left_end = X;
                used[X] = true;
            } else {
                // Default to right side
                right.push_back(X);
                right_end = X;
                used[X] = true;
            }
        } else {
            // Neither seems adjacent – use extra query
            vector<int> res_mid = ask(right_end, left_end, X);
            if (contains_pair(res_mid, right_end, X)) {
                right.push_back(X);
                right_end = X;
                used[X] = true;
            } else if (contains_pair(res_mid, left_end, X)) {
                left.push_back(X);
                left_end = X;
                used[X] = true;
            } else {
                // Fallback: add to right
                right.push_back(X);
                right_end = X;
                used[X] = true;
            }
        }
    }

    // Construct the cyclic order
    vector<int> ans;
    for (int i = left.size() - 1; i >= 1; --i)
        ans.push_back(left[i]);
    ans.push_back(R);
    for (int i = 1; i < (int)right.size(); ++i)
        ans.push_back(right[i]);

    // Output answer
    cout << "!";
    for (int x : ans) cout << " " << x;
    cout << endl;
    cout.flush();

    return 0;
}
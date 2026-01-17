#include <bits/stdc++.h>
using namespace std;

int N, M;
int L;

int query_subset_without(const vector<int>& arr, const vector<char>& alive, int skip) {
    int aliveCount = 0;
    for (size_t i = 0; i < arr.size(); ++i) if (alive[i] && (int)i != skip) ++aliveCount;
    cout << "? " << aliveCount;
    for (size_t i = 0; i < arr.size(); ++i) {
        if (!alive[i] || (int)i == skip) continue;
        cout << " " << arr[i];
    }
    cout << endl;
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    return res;
}

vector<int> minimal_with_threshold(const vector<int>& U, int t) {
    vector<char> alive(U.size(), 1);
    int aliveCount = (int)U.size();
    for (int i = 0; i < (int)U.size(); ++i) {
        if (!alive[i]) continue;
        int ans = query_subset_without(U, alive, i);
        if (ans >= t) {
            alive[i] = 0;
            --aliveCount;
        }
    }
    vector<int> kept;
    kept.reserve(N * t);
    for (int i = 0; i < (int)U.size(); ++i) if (alive[i]) kept.push_back(U[i]);
    return kept;
}

void split_recursive(const vector<int>& U, int k, vector<vector<int>>& result) {
    if (k == 1) {
        result.push_back(U);
        return;
    }
    int t = k / 2;
    vector<int> left = minimal_with_threshold(U, t);
    vector<char> inLeft(L + 1, 0);
    for (int x : left) inLeft[x] = 1;
    vector<int> right;
    right.reserve(U.size() - left.size());
    for (int x : U) if (!inLeft[x]) right.push_back(x);
    split_recursive(left, t, result);
    split_recursive(right, k - t, result);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> N >> M)) return 0;
    L = N * M;

    vector<int> all(L);
    for (int i = 0; i < L; ++i) all[i] = i + 1;

    vector<vector<int>> sticks;
    sticks.reserve(M);
    split_recursive(all, M, sticks);

    for (int i = 0; i < M; ++i) {
        cout << "!" ;
        for (int x : sticks[i]) cout << " " << x;
        cout << endl;
        cout.flush();
    }
    return 0;
}
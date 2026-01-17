#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int N, M;
    cin >> N >> M;
    int L = N * M;

    vector<bool> used(L + 1, false);
    vector<int> available;
    for (int i = 1; i <= L; ++i) {
        available.push_back(i);
    }

    for (int stick = 0; stick < M; ++stick) {
        vector<int> cur;
        for (int idx : available) {
            if (!used[idx]) {
                cur.push_back(idx);
            }
        }
        vector<int> candidates = cur;
        vector<bool> in_cur(L + 1, false);
        for (int idx : cur) in_cur[idx] = true;

        for (int j : candidates) {
            if (!in_cur[j]) continue;
            vector<int> query_set;
            for (int idx : cur) {
                if (idx != j) {
                    query_set.push_back(idx);
                }
            }
            cout << "? " << query_set.size();
            for (int x : query_set) cout << " " << x;
            cout << endl;
            int resp;
            cin >> resp;
            if (resp >= 1) {
                in_cur[j] = false;
            }
        }
        vector<int> stick_indices;
        for (int idx : cur) {
            if (in_cur[idx]) {
                stick_indices.push_back(idx);
            }
        }
        cout << "!";
        for (int x : stick_indices) cout << " " << x;
        cout << endl;
        for (int x : stick_indices) {
            used[x] = true;
        }
        vector<int> new_available;
        for (int idx : available) {
            if (!used[idx]) {
                new_available.push_back(idx);
            }
        }
        available = new_available;
    }
    return 0;
}
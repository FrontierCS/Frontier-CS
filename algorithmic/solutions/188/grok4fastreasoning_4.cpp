#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    string S1, S2;
    cin >> S1 >> S2;
    int N = S1.size();
    int M = S2.size();
    auto getid = [](char ch) -> int {
        if (isdigit(ch)) return ch - '0';
        return 10 + (ch - 'A');
    };
    vector<vector<int>> pos1(36), pos2(36);
    for (int i = 0; i < N; i++) {
        int id = getid(S1[i]);
        pos1[id].push_back(i);
    }
    for (int i = 0; i < M; i++) {
        int id = getid(S2[i]);
        pos2[id].push_back(i);
    }
    // Z1: iterate over S1 using pos2
    string Z1 = "";
    int last1a = -1;
    int last2a = -1;
    for (int r = 0; r < N; r++) {
        int id = getid(S1[r]);
        auto& vec = pos2[id];
        auto it = lower_bound(vec.begin(), vec.end(), last2a + 1);
        if (it != vec.end()) {
            Z1 += S1[r];
            last2a = *it;
            last1a = r;
        }
    }
    // Z2: iterate over S2 using pos1
    string Z2 = "";
    int last1b = -1;
    int last2b = -1;
    for (int r = 0; r < M; r++) {
        int id = getid(S2[r]);
        auto& vec = pos1[id];
        auto it = lower_bound(vec.begin(), vec.end(), last1b + 1);
        if (it != vec.end()) {
            Z2 += S2[r];
            last1b = *it;
            last2b = r;
        }
    }
    // Output the longer one
    if (Z1.size() >= Z2.size()) {
        cout << Z1 << endl;
    } else {
        cout << Z2 << endl;
    }
    return 0;
}
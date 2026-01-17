#include <bits/stdc++.h>
using namespace std;

int query(const vector<int>& v) {
    cout << "Query " << v.size();
    for (int x : v) cout << " " << x;
    cout << endl;
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;
    vector<int> S;
    vector<pair<int,int>> answers;
    S.reserve(N);
    answers.reserve(N);
    
    for (int i = 1; i <= 2 * N; ++i) {
        vector<int> q = S;
        q.push_back(i);
        int res = query(q);
        if (res == (int)S.size() + 1) {
            S.push_back(i);
        } else {
            int l = 0, r = (int)S.size();
            while (l + 1 < r) {
                int m = (l + r) / 2;
                vector<int> sub(S.begin() + l, S.begin() + m);
                sub.push_back(i);
                int res2 = query(sub);
                if (res2 == (int)sub.size() - 1) r = m;
                else l = m;
            }
            int mate = S[l];
            answers.emplace_back(i, mate);
            S.erase(S.begin() + l);
        }
    }
    
    for (auto &p : answers) {
        cout << "Answer " << p.first << " " << p.second << endl;
        cout.flush();
    }
    return 0;
}
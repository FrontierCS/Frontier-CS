#include <bits/stdc++.h>
using namespace std;

int main() {
    int N;
    cin >> N;
    int total = 2 * N;
    vector<bool> inS(total + 1, false);
    vector<int> current_list;
    for (int t = 1; t <= total; t++) {
        if (inS[t]) continue;
        vector<int> qlist = current_list;
        qlist.push_back(t);
        cout << "Query " << qlist.size();
        for (int id : qlist) cout << " " << id;
        cout << endl;
        int res;
        cin >> res;
        if (res == (int)current_list.size() + 1) {
            current_list.push_back(t);
            inS[t] = true;
        }
    }
    vector<int> SS = current_list;
    vector<int> TT;
    for (int i = 1; i <= total; i++) {
        if (!inS[i]) TT.push_back(i);
    }
    vector<pair<int, int>> ans_pairs;
    for (int iu = 0; iu < N; iu++) {
        int u = TT[iu];
        int lo = 0;
        int hi = N - 1;
        while (lo < hi) {
            int md = lo + (hi - lo) / 2;
            vector<int> AA;
            for (int j = lo; j <= md; j++) {
                AA.push_back(SS[j]);
            }
            int a_size = AA.size();
            vector<int> qlist = AA;
            qlist.push_back(u);
            cout << "Query " << qlist.size();
            for (int id : qlist) cout << " " << id;
            cout << endl;
            int res;
            cin >> res;
            if (res == a_size) {
                hi = md;
            } else {
                lo = md + 1;
            }
        }
        int partner = SS[lo];
        int a1 = min(u, partner);
        int a2 = max(u, partner);
        ans_pairs.emplace_back(a1, a2);
    }
    for (auto& p : ans_pairs) {
        cout << "Answer " << p.first << " " << p.second << endl;
    }
    return 0;
}
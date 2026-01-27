#include <bits/stdc++.h>
using namespace std;

static int N;

static void printVec(const vector<int>& v) {
    for (int i = 0; i < (int)v.size(); i++) {
        if (i) cout << ' ';
        cout << v[i];
    }
    cout << '\n';
}

static int ask(const vector<int>& L, const vector<int>& R) {
    cout << "? " << (int)L.size() << " " << (int)R.size() << "\n";
    printVec(L);
    printVec(R);
    cout.flush();

    int F;
    if (!(cin >> F)) exit(0);
    if (F == -2) exit(0);
    return F;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        cin >> N;

        vector<vector<int>> groups;
        groups.reserve(N);
        for (int i = 1; i <= N; i++) groups.push_back({i});

        vector<int> A, B;
        while (true) {
            vector<vector<int>> ng;
            ng.reserve((groups.size() + 1) / 2);

            for (int i = 0; i + 1 < (int)groups.size(); i += 2) {
                int F = ask(groups[i], groups[i + 1]);
                if (F != 0) {
                    A = groups[i];
                    B = groups[i + 1];
                    goto found_pair;
                } else {
                    vector<int> merged;
                    merged.reserve(groups[i].size() + groups[i + 1].size());
                    merged.insert(merged.end(), groups[i].begin(), groups[i].end());
                    merged.insert(merged.end(), groups[i + 1].begin(), groups[i + 1].end());
                    ng.push_back(std::move(merged));
                }
            }
            if (groups.size() & 1) ng.push_back(std::move(groups.back()));
            groups = std::move(ng);

            if ((int)groups.size() <= 1) break;
        }
found_pair:

        if (A.size() > B.size()) swap(A, B); // A is the smaller reference set

        vector<char> inA(N + 1, 0);
        for (int x : A) inA[x] = 1;

        vector<int> ans;
        ans.reserve(N);

        vector<int> single(1);
        for (int i = 1; i <= N; i++) {
            single[0] = i;
            int F;
            if (!inA[i]) {
                F = ask(A, single);
            } else {
                F = ask(B, single);
            }
            if (F == 0) ans.push_back(i);
        }

        cout << "! " << ans.size();
        for (int x : ans) cout << ' ' << x;
        cout << "\n";
        cout.flush();
    }
    return 0;
}
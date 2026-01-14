#include <bits/stdc++.h>
using namespace std;

int N, M;
long long L;

int query(const vector<int>& S) {
    cout << "? " << S.size();
    for (int x : S) cout << " " << x;
    cout << endl;
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    return res;
}

void answer(const vector<int>& stick) {
    cout << "!" ;
    for (int x : stick) cout << " " << x;
    cout << endl;
    cout.flush();
}

vector<int> minimal_subset_with_t(const vector<int>& U, int t) {
    vector<int> cur = U;
    for (size_t pos = 0; pos < cur.size();) {
        vector<int> sub;
        sub.reserve(cur.size() - 1);
        for (size_t j = 0; j < cur.size(); ++j) if (j != pos) sub.push_back(cur[j]);
        int res = query(sub);
        if (res >= t) {
            cur.erase(cur.begin() + pos);
        } else {
            ++pos;
        }
    }
    return cur;
}

void solve(const vector<int>& U, int t) {
    if (t == 1) {
        vector<int> S = U;
        if ((int)S.size() != N) {
            S = minimal_subset_with_t(U, 1);
        }
        answer(S);
        return;
    }
    int tl = t / 2;
    int tr = t - tl;
    vector<int> A = minimal_subset_with_t(U, tl);
    vector<char> inA(L + 1, false);
    for (int x : A) inA[x] = true;
    vector<int> B; B.reserve(U.size() - A.size());
    for (int x : U) if (!inA[x]) B.push_back(x);
    solve(A, tl);
    solve(B, tr);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if (!(cin >> N >> M)) return 0;
    L = 1LL * N * M;
    vector<int> U; U.reserve(L);
    for (int i = 1; i <= N * M; ++i) U.push_back(i);
    solve(U, M);
    return 0;
}
#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if (!(cin >> N)) return 0;
    vector<int> S(N);
    for (int i = 0; i < N; ++i) cin >> S[i];
    int M;
    cin >> M;
    vector<pair<int,int>> jerry(M);
    for (int i = 0; i < M; ++i) {
        int x, y; cin >> x >> y;
        jerry[i] = {x, y};
    }

    vector<int> pos(N);
    for (int i = 0; i < N; ++i) pos[S[i]] = i;

    auto is_correct = [&](int i)->bool { return S[i] == i; };

    set<int> bad;
    for (int i = 0; i < N; ++i) if (!is_correct(i)) bad.insert(i);

    auto upd_bad = [&](int i){
        bool ok = is_correct(i);
        if (ok) {
            auto it = bad.find(i);
            if (it != bad.end()) bad.erase(it);
        } else {
            bad.insert(i);
        }
    };

    auto do_swap = [&](int i, int j){
        if (i == j) return;
        // update pos and S
        int a = S[i], b = S[j];
        swap(S[i], S[j]);
        pos[a] = j; pos[b] = i;
    };

    long long sumCost = 0;
    vector<pair<int,int>> myMoves;

    if (bad.empty()) {
        cout << 0 << "\n";
        cout << 0 << "\n";
        return 0;
    }

    int R = 0;
    for (int k = 0; k < M; ++k) {
        // Jerry's move
        int x = jerry[k].first, y = jerry[k].second;
        // update bad for x,y before and after
        upd_bad(x); upd_bad(y);
        do_swap(x, y);
        upd_bad(x); upd_bad(y);

        int u = 0, v = 0;
        if (!bad.empty()) {
            int i = *bad.begin(); // pick smallest incorrect index
            int j = pos[i];       // position where value i currently is
            // We'll swap i and j
            // Update bad for affected indices before and after
            upd_bad(i); upd_bad(j);
            do_swap(i, j);
            upd_bad(i); upd_bad(j);
            u = i; v = j;
        } else {
            // already sorted after Jerry; do dummy swap
            u = v = 0;
        }

        myMoves.emplace_back(u, v);
        sumCost += llabs((long long)u - (long long)v);
        R = k + 1;

        if (bad.empty()) {
            break;
        }
    }

    // If not sorted by M, we did our best; ensure compliance (though problem guarantees possible)
    if (!bad.empty()) {
        // Fill remaining with dummy if any (but must not exceed M)
        // However, array isn't sorted; but per problem guarantee this should not happen.
        // We'll output all M rounds done so far (R already equals M here) and hope inputs respect guarantee.
    }

    cout << R << "\n";
    for (int i = 0; i < R; ++i) {
        cout << myMoves[i].first << " " << myMoves[i].second << "\n";
    }
    long long V = sumCost * (long long)R;
    cout << V << "\n";
    return 0;
}
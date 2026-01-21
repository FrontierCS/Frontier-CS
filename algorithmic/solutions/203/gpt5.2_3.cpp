#include <bits/stdc++.h>
using namespace std;

static int query_count = 0;

static int Query(const vector<int>& v) {
    ++query_count;
    cout << "Query " << (int)v.size();
    for (int x : v) cout << ' ' << x;
    cout << endl; // flush
    int res;
    if (!(cin >> res)) exit(0);
    if (res < 0) exit(0);
    return res;
}

static void Answer(int a, int b) {
    cout << "Answer " << a << ' ' << b << endl; // flush
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    int M = 2 * N;

    vector<int> S;
    S.reserve(N + 5);

    int answered = 0;

    auto find_conflict = [&](int x) -> int {
        // Assumes Query(S) == |S| and Query(S + x) < |S|+1, and exactly one element conflicts.
        int l = 0, r = (int)S.size() - 1;
        while (l < r) {
            int mid = (l + r) >> 1;
            vector<int> sub;
            sub.reserve(mid - l + 2);
            for (int i = l; i <= mid; i++) sub.push_back(S[i]);
            sub.push_back(x);
            int res = Query(sub);
            if (res == (int)sub.size()) {
                l = mid + 1;
            } else {
                r = mid;
            }
        }
        return S[l];
    };

    for (int x = 1; x <= M; x++) {
        if (answered == N) break;

        vector<int> tmp = S;
        tmp.push_back(x);
        int res = Query(tmp);

        if (res == (int)tmp.size()) {
            S.push_back(x);
        } else {
            int y = find_conflict(x);
            Answer(x, y);
            answered++;

            // remove y from S
            for (int i = 0; i < (int)S.size(); i++) {
                if (S[i] == y) {
                    S[i] = S.back();
                    S.pop_back();
                    break;
                }
            }
        }
    }

    // If any remain (shouldn't), pair arbitrarily (best-effort).
    // NOTE: Interactive judges would mark wrong if reached; kept to avoid hanging.
    while (answered < N && (int)S.size() >= 2) {
        int a = S.back(); S.pop_back();
        int b = S.back(); S.pop_back();
        Answer(a, b);
        answered++;
    }

    return 0;
}
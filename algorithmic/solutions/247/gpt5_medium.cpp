#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if (!(cin >> N)) return 0;
    vector<long long> A(N), B(N);
    for (int i = 0; i < N; ++i) cin >> A[i];
    for (int i = 0; i < N; ++i) cin >> B[i];
    long long sa = 0, sb = 0;
    for (auto x : A) sa += x;
    for (auto x : B) sb += x;
    if (N == 2) {
        if (A == B) {
            cout << "Yes\n0\n";
            return 0;
        }
        // Single possible operation (1,2)
        vector<long long> C = A;
        long long a1 = C[0], a2 = C[1];
        C[0] = a2 - 1;
        C[1] = a1 + 1;
        if (C == B) {
            cout << "Yes\n1\n1 2\n";
        } else {
            cout << "No\n";
        }
        return 0;
    }
    if (sa != sb) {
        cout << "No\n";
        return 0;
    }
    // Heuristic greedy to try reach B
    vector<pair<int,int>> ops;
    auto do_op = [&](int i, int j){
        // i<j 1-indexed when recording
        long long ai = A[i], aj = A[j];
        A[i] = aj - 1;
        A[j] = ai + 1;
        ops.emplace_back(i+1, j+1);
    };
    // Try multiple passes to reduce L1 distance
    auto dist = [&](){
        long long d=0;
        for(int i=0;i<N;i++) d += llabs(A[i]-B[i]);
        return d;
    };
    long long curd = dist();
    int max_iter = 200000; // cap
    bool improved = true;
    while (curd > 0 && max_iter-- > 0) {
        bool moved = false;
        // Try to fix indices one by one
        for (int i = 0; i < N && curd > 0; ++i) {
            if (A[i] == B[i]) continue;
            if (A[i] < B[i]) {
                // find j>i with A[j] == B[i] + 1
                int jbest = -1;
                for (int j = N-1; j > i; --j) {
                    if (A[j] == B[i] + 1) { jbest = j; break; }
                }
                if (jbest != -1) {
                    do_op(i, jbest);
                    moved = true;
                    curd = dist();
                    if (curd==0) break;
                    continue;
                }
                // else try any j>i that reduces distance
                long long bestDelta = 0;
                int jb = -1;
                for (int j = i+1; j < N; ++j) {
                    long long ai = A[i], aj = A[j];
                    long long ni = aj - 1, nj = ai + 1;
                    long long before = llabs(ai - B[i]) + llabs(aj - B[j]);
                    long long after  = llabs(ni - B[i]) + llabs(nj - B[j]);
                    long long delta = before - after;
                    if (delta > bestDelta) {
                        bestDelta = delta;
                        jb = j;
                    }
                }
                if (jb != -1) {
                    do_op(i, jb);
                    moved = true;
                    curd = dist();
                    if (curd==0) break;
                }
            } else {
                // A[i] > B[i], try j<i with A[j] == B[i] - 1
                int jbest = -1;
                for (int j = 0; j < i; ++j) {
                    if (A[j] == B[i] - 1) { jbest = j; }
                }
                if (jbest != -1) {
                    do_op(jbest, i);
                    moved = true;
                    curd = dist();
                    if (curd==0) break;
                    continue;
                }
                // else try any j<i that reduces distance
                long long bestDelta = 0;
                int jb = -1;
                for (int j = 0; j < i; ++j) {
                    long long aj = A[j], ai = A[i];
                    long long nj = ai - 1, ni = aj + 1; // since op(j,i)
                    long long before = llabs(ai - B[i]) + llabs(aj - B[j]);
                    long long after  = llabs(ni - B[i]) + llabs(nj - B[j]);
                    long long delta = before - after;
                    if (delta > bestDelta) {
                        bestDelta = delta;
                        jb = j;
                    }
                }
                if (jb != -1) {
                    do_op(jb, i);
                    moved = true;
                    curd = dist();
                    if (curd==0) break;
                }
            }
        }
        if (!moved) {
            // Try random helpful move
            bool any = false;
            for (int i = 0; i < N && !any; ++i) {
                for (int j = i+1; j < N && !any; ++j) {
                    long long ai = A[i], aj = A[j];
                    long long ni = aj - 1, nj = ai + 1;
                    long long before = llabs(ai - B[i]) + llabs(aj - B[j]);
                    long long after  = llabs(ni - B[i]) + llabs(nj - B[j]);
                    if (after <= before) {
                        do_op(i, j);
                        any = true;
                        curd = dist();
                    }
                }
            }
            if (!any) break;
        }
    }
    if (A == B) {
        cout << "Yes\n";
        cout << ops.size() << "\n";
        for (auto &p : ops) cout << p.first << " " << p.second << "\n";
    } else {
        cout << "No\n";
    }
    return 0;
}
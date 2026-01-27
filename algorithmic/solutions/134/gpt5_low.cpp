#include <bits/stdc++.h>
using namespace std;

using int64 = long long;

struct Constraint {
    long long x, y;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;

    long long La = 1, Lb = 1; // lower bounds for a and b
    vector<Constraint> cons;  // constraints from response 3: not (a<=x and b<=y)
    set<pair<long long,long long>> cons_set; // to avoid duplicate constraints

    auto compute_candidate = [&]() -> pair<long long,long long> {
        // Build helper structure: for Y(A) = max y over constraints with x >= A
        // Sort constraints by x descending and build prefix max of y
        vector<pair<long long,long long>> pts; // (x, y)
        pts.reserve(cons.size());
        for (auto &c : cons) {
            long long x = min(c.x, n);
            long long y = min(c.y, n);
            pts.emplace_back(x, y);
        }
        sort(pts.begin(), pts.end(), [&](const auto& a, const auto& b){
            if (a.first != b.first) return a.first > b.first; // desc by x
            return a.second > b.second;
        });
        // compress x keys and build max_y_so_far
        vector<long long> xkeys;
        vector<long long> maxY;
        long long curMaxY = LLONG_MIN;
        long long lastX = LLONG_MIN;
        for (auto &p : pts) {
            if (p.first != lastX) {
                xkeys.push_back(p.first);
                curMaxY = max(curMaxY, p.second);
                maxY.push_back(curMaxY);
                lastX = p.first;
            } else {
                curMaxY = max(curMaxY, p.second);
                maxY.back() = max(maxY.back(), p.second);
            }
        }
        // Now ensure maxY is prefix max (already maintained as we go)
        // Prepare candidate A values: La and xi+1
        vector<long long> candidatesA;
        candidatesA.push_back(La);
        for (auto &p : pts) {
            if (p.first < n) {
                long long A = max(La, p.first + 1);
                candidatesA.push_back(A);
            }
        }
        // deduplicate candidates
        sort(candidatesA.begin(), candidatesA.end());
        candidatesA.erase(unique(candidatesA.begin(), candidatesA.end()), candidatesA.end());

        auto Y_of_A = [&](long long A) -> long long {
            // find max y over constraints with x >= A
            if (xkeys.empty()) return LLONG_MIN; // no constraints => -inf
            // xkeys is descending. Find first index i with xkeys[i] >= A.
            // Since descending, we can use custom binary search.
            int l = 0, r = (int)xkeys.size()-1, ans = -1;
            while (l <= r) {
                int m = (l + r) / 2;
                if (xkeys[m] >= A) { ans = m; l = m + 1; }
                else r = m - 1;
            }
            if (ans == -1) return LLONG_MIN;
            return maxY[ans];
        };

        // Choose candidate minimizing A + B where B = max(Lb, Y(A)+1), with bounds <= n
        long long bestA = La, bestB = Lb;
        __int128 bestSum = (__int128)LLONG_MAX;
        for (long long A : candidatesA) {
            if (A > n) continue;
            long long Y = Y_of_A(A);
            long long B;
            if (Y == LLONG_MIN) B = Lb;
            else {
                if (Y == LLONG_MAX) continue;
                B = max(Lb, Y + 1);
            }
            if (B > n) continue;
            __int128 sum = (__int128)A + (__int128)B;
            if (sum < bestSum) {
                bestSum = sum;
                bestA = A;
                bestB = B;
            }
        }
        // As a fallback in case no candidates produced (shouldn't happen), clamp to [La..n],[Lb..n]
        if (bestSum == (__int128)LLONG_MAX) {
            long long A = min(La, n);
            long long Y = Y_of_A(A);
            long long B = (Y == LLONG_MIN ? Lb : max(Lb, Y + 1));
            if (B > n) B = n;
            bestA = max(La, 1LL);
            bestB = max(Lb, 1LL);
            bestA = min(bestA, n);
            bestB = min(bestB, n);
        }
        return {bestA, bestB};
    };

    for (int iter = 0; iter < 100000; ++iter) {
        auto [A, B] = compute_candidate();
        cout << A << " " << B << endl;
        cout.flush();

        int resp;
        if (!(cin >> resp)) return 0;
        if (resp == 0) {
            return 0;
        } else if (resp == 1) {
            La = max(La, A + 1);
            if (La > n) La = n; // safety
        } else if (resp == 2) {
            Lb = max(Lb, B + 1);
            if (Lb > n) Lb = n;
        } else if (resp == 3) {
            if (A <= n && B <= n) {
                if (!cons_set.count({A,B})) {
                    cons.push_back({A,B});
                    cons_set.insert({A,B});
                } else {
                    // If duplicate and we're stuck, try nudging one step to avoid cycles
                    long long nA = min(n, A + 1);
                    long long nB = min(n, B + 1);
                    if (!cons_set.count({nA, B})) {
                        cons.push_back({nA, B});
                        cons_set.insert({nA, B});
                    } else if (!cons_set.count({A, nB})) {
                        cons.push_back({A, nB});
                        cons_set.insert({A, nB});
                    }
                }
            }
        } else {
            // Invalid, terminate
            return 0;
        }
    }
    return 0;
}
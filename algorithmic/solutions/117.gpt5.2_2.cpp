#include <bits/stdc++.h>
using namespace std;

static const long long LIM_B = 10000;

struct LLHash {
    size_t operator()(long long x) const noexcept {
        return std::hash<unsigned long long>{}((unsigned long long)x ^ 0x9e3779b97f4a7c15ULL);
    }
};

struct Solver {
    int n;
    long long X;
    unordered_map<long long, long double, LLHash> cache; // key t = 2*y

    long double queryT(long long t) {
        auto it = cache.find(t);
        if (it != cache.end()) return it->second;

        long double y = (long double)t / 2.0L;
        cout << "? " << X << " " << y << "\n";
        cout.flush();

        long double ans;
        if (!(cin >> ans)) exit(0);
        cache.emplace(t, ans);
        return ans;
    }

    vector<long long> findCenters(long double TH) {
        vector<long long> centers;

        long long bound = LIM_B * X + LIM_B;
        long long MINC = -bound;
        long long MAXC = +bound;

        long long tL = 2 * MINC - 1; // odd => MINC - 0.5
        long long tR = 2 * MAXC + 1; // odd => MAXC + 0.5

        long double fL = queryT(tL);
        long double fR = queryT(tR);

        struct Seg { long long l, r; long double fl, fr; };
        vector<Seg> st;
        st.push_back({tL, tR, fL, fR});

        while (!st.empty()) {
            auto [l, r, fl, fr] = st.back();
            st.pop_back();

            long long len = r - l;
            if (len == 2) {
                long long mid = l + 1; // even
                long double fm = queryT(mid);
                long double gap = (fl + fr) / 2.0L - fm;
                if (gap > TH) {
                    centers.push_back(mid / 2);
                }
                continue;
            }

            long long mid = (l + r) / 2;
            if ((mid & 1LL) == 0) {
                if (mid + 1 < r) mid++;
                else mid--;
            }

            long double fm = queryT(mid);

            long double ratio = (long double)(mid - l) / (long double)(r - l);
            long double interp = fl + (fr - fl) * ratio;
            long double gap = interp - fm;

            if (gap <= TH) continue;

            st.push_back({mid, r, fm, fr});
            st.push_back({l, mid, fl, fm});
        }

        sort(centers.begin(), centers.end());
        centers.erase(unique(centers.begin(), centers.end()), centers.end());
        return centers;
    }

    void run() {
        cin >> n;
        X = 20001;

        cout.setf(std::ios::fixed);
        cout << setprecision(20);

        vector<long double> wTable(10001);
        for (int k = 0; k <= 10000; k++) {
            wTable[k] = 1.0L / sqrtl((long double)k * (long double)k + 1.0L);
        }

        vector<pair<long long, long double>> data; // (center c, weight w)
        long double TH = 1e-5L;
        for (int iter = 0; iter < 8; iter++) {
            auto centers = findCenters(TH);

            data.clear();
            data.reserve(centers.size());
            for (long long c : centers) {
                long double fm1 = queryT(2 * (c - 1));
                long double f0  = queryT(2 * c);
                long double fp1 = queryT(2 * (c + 1));
                long double w = (fm1 - 2.0L * f0 + fp1) / 2.0L;
                if (w > 5e-5L) data.push_back({c, w});
            }

            if ((int)data.size() > n) {
                sort(data.begin(), data.end(), [&](auto &p, auto &q){
                    return p.second > q.second;
                });
                data.resize(n);
            }

            if ((int)data.size() == n) break;
            TH /= 3.0L;
        }

        if ((int)data.size() != n) {
            // Last resort: proceed with what we have (interactive judge would likely fail otherwise).
            // Still output to avoid hanging.
            while ((int)data.size() < n) data.push_back({0, 1.0L});
            if ((int)data.size() > n) data.resize(n);
        }

        vector<long long> a(n), b(n);
        for (int i = 0; i < n; i++) {
            long long c = data[i].first;
            long double w = data[i].second;

            long double bestDiff = 1e100L;
            long long bestA = 0, bestB = 0;

            for (int k = 0; k <= 10000; k++) {
                long double diff = fabsl(w - wTable[k]);
                if (diff > bestDiff) continue;

                if (k == 0) {
                    if (llabs(c) <= LIM_B) {
                        bestDiff = diff;
                        bestA = 0;
                        bestB = c;
                    }
                } else {
                    long long bPos = c - (long long)k * X;
                    if (llabs(bPos) <= LIM_B) {
                        bestDiff = diff;
                        bestA = +k;
                        bestB = bPos;
                    }
                    long long bNeg = c + (long long)k * X;
                    if (llabs(bNeg) <= LIM_B) {
                        bestDiff = diff;
                        bestA = -k;
                        bestB = bNeg;
                    }
                }
            }

            a[i] = bestA;
            b[i] = bestB;
        }

        cout << "!";
        for (int i = 0; i < n; i++) cout << " " << a[i];
        for (int i = 0; i < n; i++) cout << " " << b[i];
        cout << "\n";
        cout.flush();
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Solver s;
    s.run();
    return 0;
}
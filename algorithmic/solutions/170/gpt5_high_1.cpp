#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N; long long L;
    if(!(cin >> N >> L)) return 0;
    vector<long long> T(N);
    for(int i=0;i<N;i++) cin >> T[i];

    // Build a cycle a_i by sorting employees by T ascending
    vector<int> ord(N); iota(ord.begin(), ord.end(), 0);
    stable_sort(ord.begin(), ord.end(), [&](int i, int j){
        if (T[i] != T[j]) return T[i] < T[j];
        return i < j;
    });
    vector<int> a(N);
    for(int k=0;k<N;k++){
        int i = ord[k];
        int j = ord[(k+1)%N];
        a[i] = j;
    }

    auto assign_b = [&](const vector<double>& w)->vector<int>{
        // r_j = 2*w_j - w_pred(j)
        vector<int> pred(N, -1);
        for(int i=0;i<N;i++) pred[a[i]] = i;
        vector<double> r(N, 0.0), y(N, 0.0);
        for(int j=0;j<N;j++){
            r[j] = 2.0*w[j] - w[pred[j]];
        }
        vector<int> idx(N); iota(idx.begin(), idx.end(), 0);
        stable_sort(idx.begin(), idx.end(), [&](int i, int j){
            if (w[i] != w[j]) return w[i] > w[j];
            return i < j;
        });
        vector<int> b(N, 0);
        const double EPS = 1e-12;
        // For tie-breaking random but deterministic
        for(int ii=0; ii<N; ii++){
            int i = idx[ii];
            double wi = w[i];
            double bestDelta = 1e300;
            double bestTie = 1e300;
            int bestj = 0;
            for(int j=0;j<N;j++){
                double before = fabs(y[j] - r[j]);
                double after  = fabs((y[j] + wi) - r[j]);
                double d = after - before;
                double tie = y[j] - r[j];
                if (d < bestDelta - EPS || (fabs(d - bestDelta) <= EPS && tie < bestTie - EPS) || (fabs(d - bestDelta) <= EPS && fabs(tie - bestTie) <= EPS && j < bestj)) {
                    bestDelta = d;
                    bestTie = tie;
                    bestj = j;
                }
            }
            b[i] = bestj;
            y[bestj] += wi;
        }
        return b;
    };

    auto stationary = [&](const vector<int>& a, const vector<int>& b, double alpha, int iters)->vector<double>{
        int n = a.size();
        vector<double> v(n, 1.0/n), nv(n, 0.0);
        for(int it=0; it<iters; it++){
            fill(nv.begin(), nv.end(), 0.0);
            for(int i=0;i<n;i++){
                if (a[i] == b[i]) {
                    nv[a[i]] += v[i];
                } else {
                    nv[a[i]] += 0.5 * v[i];
                    nv[b[i]] += 0.5 * v[i];
                }
            }
            double uni = (1.0 - alpha) / n;
            for(int j=0;j<n;j++){
                nv[j] = alpha * nv[j] + uni;
            }
            v.swap(nv);
        }
        // Normalize just in case
        double s = 0.0; for(double x: v) s += x;
        if (s > 0) for(double &x: v) x /= s;
        return v;
    };

    // Iterative refinement
    vector<double> w(N);
    for(int i=0;i<N;i++) w[i] = (double)T[i];

    vector<int> bestA = a, bestB(N, 0);
    double bestPredErr = 1e300;

    int OUTER_ITERS = 6;
    const double alpha = 0.995;
    const int PI_ITERS = 2000;

    for(int iter=0; iter<OUTER_ITERS; iter++){
        vector<int> b = assign_b(w);

        // Small perturbation to avoid degenerate periodic cases: ensure at least one b differs from a
        bool allEq = true;
        for(int i=0;i<N;i++) if (b[i] != a[i]) { allEq = false; break; }
        if (allEq) {
            // change one arbitrarily
            b[0] = (a[0] + 1) % N;
        }

        vector<double> pi = stationary(a, b, alpha, PI_ITERS);

        // Predicted error
        double predErr = 0.0;
        for(int i=0;i<N;i++){
            double ti = (double)L * pi[i];
            predErr += fabs(ti - (double)T[i]);
        }
        if (predErr < bestPredErr) {
            bestPredErr = predErr;
            bestB = b;
        }

        // Update w towards target and current predicted distribution
        for(int i=0;i<N;i++){
            double ti = (double)L * pi[i];
            w[i] = 0.5 * (double)T[i] + 0.5 * ti;
        }
    }

    // Output
    for(int i=0;i<N;i++){
        cout << a[i] << " " << bestB[i] << "\n";
    }
    return 0;
}
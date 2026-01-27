#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long n, m;
    if (!(cin >> n >> m)) return 0;

    // Trivial fallback: if either dimension is 0 (not possible by constraints) or 1x1
    if (n == 0 || m == 0) {
        cout << 0 << "\n";
        return 0;
    }
    if (n == 1 && m == 1) {
        cout << 1 << "\n1 1\n";
        return 0;
    }

    // Generate primes up to 1000
    int LIM = 1000;
    vector<int> primes;
    vector<bool> isComposite(LIM+1,false);
    for (int i=2;i<=LIM;i++){
        if(!isComposite[i]){
            primes.push_back(i);
            for(long long j=1LL*i*i;j<=LIM;j+=i) isComposite[j]=true;
        }
    }

    struct Plan {
        long double approx;
        int q;
        bool rowsAreLines; // true: rows=lines, cols=points; false: rows=points, cols=lines
        long long rlim, clim;
    };
    Plan best{ -1.0L, 2, true, 0, 0 };

    for (int q : primes) {
        long long P = 1LL*q*q;         // points
        long long L = 1LL*q*(q+1);     // lines
        // Orientation 0: rows=lines, cols=points
        {
            long long r = min(n, L);
            long long c = min(m, P);
            long double approxDeg = (P ? ( (long double)q * (long double)c / (long double)P ) : 0.0L);
            long double approxE = (long double)r * approxDeg;
            if (approxE > best.approx) {
                best = {approxE, q, true, r, c};
            }
        }
        // Orientation 1: rows=points, cols=lines
        {
            long long r = min(n, P);
            long long c = min(m, L);
            long double approxDeg = (L ? ( (long double)(q+1) * (long double)c / (long double)L ) : 0.0L);
            long double approxE = (long double)r * approxDeg;
            if (approxE > best.approx) {
                best = {approxE, q, false, r, c};
            }
        }
    }

    // If no good plan (very small m,n), fallback to single row/column
    if (best.approx <= 0.0L) {
        if (m >= n) {
            cout << m << "\n";
            for (int c=1;c<=m;c++) cout << 1 << " " << c << "\n";
        } else {
            cout << n << "\n";
            for (int r=1;r<=n;r++) cout << r << " " << 1 << "\n";
        }
        return 0;
    }

    int q = best.q;
    long long P = 1LL*q*q;
    long long L = 1LL*q*(q+1);

    long long rlim = best.rlim;
    long long clim = best.clim;

    vector<pair<int,int>> ans; ans.reserve( (size_t)min(rlim* (long long)(q+1), n*m) );

    auto pointIndex = [q](int x, int y)->long long {
        return 1LL*x*q + y; // 0..q^2-1
    };
    auto lineIndexNV = [q](int a, int b)->long long {
        return 1LL*a*q + b; // 0..q^2-1 (non-vertical)
    };
    auto lineIndexV = [q](int c)->long long {
        return 1LL*q*q + c; // q^2..q^2+q-1 (vertical)
    };

    if (best.rowsAreLines) {
        // Rows = lines (non-vertical first, then vertical)
        // Cols = points
        // Use first rlim lines and first clim points
        for (long long ri = 0; ri < rlim; ++ri) {
            if (ri < (long long)q*q) {
                int a = (int)(ri / q);
                int b = (int)(ri % q);
                for (int x = 0; x < q; ++x) {
                    int y = ( (1LL*a * x + b) % q );
                    long long pid = pointIndex(x,y);
                    if (pid < clim) {
                        // grid row index = ri+1, col index = pid+1
                        ans.emplace_back((int)ri+1, (int)pid+1);
                    }
                }
            } else {
                int c0 = (int)(ri - 1LL*q*q);
                // vertical x = c0
                for (int y = 0; y < q; ++y) {
                    long long pid = pointIndex(c0, y);
                    if (pid < clim) {
                        ans.emplace_back((int)ri+1, (int)pid+1);
                    }
                }
            }
        }
    } else {
        // Rows = points
        // Cols = lines
        for (long long ri = 0; ri < rlim; ++ri) {
            int x = (int)(ri / q);
            int y = (int)(ri % q);
            // non-vertical lines passing through (x,y): for each slope a, b = y - a x
            for (int a = 0; a < q; ++a) {
                int b = ( ( (y - (long long)a * x) % q) + q ) % q;
                long long lid = lineIndexNV(a,b);
                if (lid < clim) {
                    ans.emplace_back((int)ri+1, (int)lid+1);
                }
            }
            // vertical line x = x
            long long lidv = lineIndexV(x);
            if (lidv < clim) {
                ans.emplace_back((int)ri+1, (int)lidv+1);
            }
        }
    }

    // Ensure not exceeding n rows or m cols is already satisfied by rlim, clim.
    // Output
    cout << ans.size() << "\n";
    for (auto &p : ans) {
        cout << p.first << " " << p.second << "\n";
    }
    return 0;
}
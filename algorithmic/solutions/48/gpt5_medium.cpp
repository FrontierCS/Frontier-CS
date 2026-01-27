#include <bits/stdc++.h>
using namespace std;

struct Pt { double x,y,z; };

static inline long long mul_cap(long long a, long long b, long long cap){
    if(a==0 || b==0) return 0;
    if(a > cap / b) return cap;
    return a*b;
}
static inline long long add_cap(long long a, long long b, long long cap){
    long long s = a + b;
    if(s < a || s > cap) return cap;
    return s;
}

long long countFCC(double t, long long need){
    if(t <= 0) return 0;
    const double ROOT2 = sqrt(2.0);
    double r = t/(2.0*ROOT2);
    double range = 1.0 - 2.0*r;
    if(range < 0) return 0;
    const double eps = 1e-12;
    long long a = (long long)floor(range / t + eps) + 1;
    if(a < 0) a = 0;
    long long b = (long long)floor(range / t - 0.5 + eps) + 1;
    if(b < 0) b = 0;
    long long cap = need;
    long long a2 = mul_cap(a, a, cap);
    long long a3 = mul_cap(a2, a, cap);
    long long b2 = mul_cap(b, b, cap);
    long long ab2 = mul_cap(a, b2, cap);
    long long term2 = mul_cap(3, ab2, cap);
    long long total = add_cap(a3, term2, cap);
    return total;
}

vector<Pt> generateFCC(long long n, double &out_r){
    const double ROOT2 = sqrt(2.0);
    double lo = 0.0, hi = 1.0;
    for(int it=0; it<70; ++it){
        double mid = (lo + hi) * 0.5;
        if(countFCC(mid, n) >= n) lo = mid;
        else hi = mid;
    }
    double t = lo;
    double r = t/(2.0*ROOT2);
    // adjust slightly downward if needed
    for(int tries=0; tries<20; ++tries){
        double range = 1.0 - 2.0*r;
        const double eps = 1e-12;
        long long a = (long long)floor(range / t + eps) + 1;
        if(a < 0) a = 0;
        long long b = (long long)floor(range / t - 0.5 + eps) + 1;
        if(b < 0) b = 0;
        long long cnt = a>0 ? (a*(long long)a*(long long)a + 3LL*a*b*(long long)b) : 0LL;
        if(cnt >= n) break;
        t *= 0.999;
        r = t/(2.0*ROOT2);
    }

    vector<double> X0, X1;
    // Build coordinate lists ensuring [r, 1-r]
    for(long long i=0;;++i){
        double x = r + i*t;
        if(x <= 1.0 - r + 1e-12) X0.push_back(x);
        else break;
        if((long long)X0.size() > n) { /* enough along this axis */ }
    }
    for(long long i=0;;++i){
        double x = r + (i + 0.5)*t;
        if(x <= 1.0 - r + 1e-12) X1.push_back(x);
        else break;
        if((long long)X1.size() > n) { /* enough */ }
    }

    vector<Pt> res;
    res.reserve((size_t)min<long long>(n, (long long)X0.size()*(long long)X0.size()*(long long)X0.size() + 3LL*(long long)X0.size()*(long long)X1.size()*(long long)X1.size()));

    auto emit = [&](const vector<double>& A, const vector<double>& B, const vector<double>& C){
        for(size_t i=0; i<A.size() && (long long)res.size()<n; ++i){
            for(size_t j=0; j<B.size() && (long long)res.size()<n; ++j){
                for(size_t k=0; k<C.size() && (long long)res.size()<n; ++k){
                    res.push_back({A[i], B[j], C[k]});
                    if((long long)res.size()>=n) return;
                }
            }
        }
    };
    emit(X0, X0, X0);
    if((long long)res.size() < n){
        emit(X0, X1, X1);
    }
    if((long long)res.size() < n){
        emit(X1, X0, X1);
    }
    if((long long)res.size() < n){
        emit(X1, X1, X0);
    }

    out_r = r;
    return res;
}

vector<Pt> generateGrid(long long n, double &out_r){
    // balanced m x k x l grid
    long long z = pow((long double)n, 1.0L/3.0L);
    if(z < 1) z = 1;
    while((z+1)*(z+1)*(z+1) <= n) ++z;
    while(z*z*z > n && z>1) --z;

    long long y = sqrt((long double)n / (long double)z);
    if(y < 1) y = 1;
    while((y+1)*(y+1)*z <= n) ++y;
    while(y*y*z < n && (y+1)*y*z < n) ++y;
    while(y*y*z > n && y>1 && (y-1)*y*z >= n) --y;

    long long x = (n + (y*z - 1)) / (y*z);
    if(x < 1) x = 1;
    long long Mx = x, My = y, Mz = z;
    long long Mmax = max(Mx, max(My, Mz));
    double r = 1.0 / (2.0 * (double)Mmax);

    vector<double> X, Y, Z;
    X.reserve(Mx); Y.reserve(My); Z.reserve(Mz);
    for(long long i=0;i<Mx;++i) X.push_back((2.0*i + 1.0)*r);
    for(long long j=0;j<My;++j) Y.push_back((2.0*j + 1.0)*r);
    for(long long k=0;k<Mz;++k) Z.push_back((2.0*k + 1.0)*r);

    vector<Pt> res;
    res.reserve((size_t)n);
    for(long long i=0;i<Mx && (long long)res.size()<n;++i){
        for(long long j=0;j<My && (long long)res.size()<n;++j){
            for(long long k=0;k<Mz && (long long)res.size()<n;++k){
                res.push_back({X[i], Y[j], Z[k]});
                if((long long)res.size()>=n) break;
            }
        }
    }
    out_r = r;
    return res;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long n;
    if(!(cin >> n)) return 0;

    double r_fcc = 0.0, r_grid = 0.0;
    vector<Pt> fcc = generateFCC(n, r_fcc);
    vector<Pt> grid = generateGrid(n, r_grid);

    const vector<Pt>* best = &fcc;
    if((long long)fcc.size() < n) best = &grid;
    else if(r_grid > r_fcc) best = &grid;

    cout.setf(std::ios::fixed); 
    cout<<setprecision(12);
    for(long long i=0;i<n;++i){
        const Pt &p = (*best)[i];
        double x = min(1.0, max(0.0, p.x));
        double y = min(1.0, max(0.0, p.y));
        double z = min(1.0, max(0.0, p.z));
        cout << x << " " << y << " " << z << "\n";
    }
    return 0;
}
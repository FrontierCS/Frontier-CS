#include <bits/stdc++.h>
using namespace std;

struct Vec {
    double x, y, z;
    Vec() : x(0), y(0), z(0) {}
    Vec(double x_, double y_, double z_) : x(x_), y(y_), z(z_) {}
    Vec operator+(const Vec& o) const { return Vec(x+o.x, y+o.y, z+o.z); }
    Vec operator-(const Vec& o) const { return Vec(x-o.x, y-o.y, z-o.z); }
    Vec operator*(double k) const { return Vec(x*k, y*k, z*k); }
    Vec& operator+=(const Vec& o) { x+=o.x; y+=o.y; z+=o.z; return *this; }
    Vec& operator-=(const Vec& o) { x-=o.x; y-=o.y; z-=o.z; return *this; }
};

static inline double dot(const Vec& a, const Vec& b){ return a.x*b.x + a.y*b.y + a.z*b.z; }
static inline double norm2(const Vec& a){ return dot(a,a); }
static inline double norm(const Vec& a){ return sqrt(norm2(a)); }
static inline Vec normalize(const Vec& a){ double n = norm(a); if(n==0) return a; return a*(1.0/n); }

vector<Vec> special_points(int n){
    vector<Vec> p;
    if(n==2){
        p.push_back(Vec(0,0,1));
        p.push_back(Vec(0,0,-1));
    } else if(n==3){
        for(int k=0;k<3;k++){
            double a = 2.0*M_PI*k/3.0;
            p.push_back(Vec(cos(a), sin(a), 0));
        }
    } else if(n==4){
        vector<Vec> t = { {1,1,1}, {1,-1,-1}, {-1,1,-1}, {-1,-1,1} };
        for(auto v:t) p.push_back(normalize(v));
    } else if(n==6){
        p = { {1,0,0},{-1,0,0},{0,1,0},{0,-1,0},{0,0,1},{0,0,-1} };
    } else if(n==8){
        for(int sx=-1;sx<=1;sx+=2)
            for(int sy=-1;sy<=1;sy+=2)
                for(int sz=-1;sz<=1;sz+=2)
                    p.push_back(normalize(Vec(sx,sy,sz)));
    } else if(n==12){
        double phi = (1.0 + sqrt(5.0))/2.0;
        double inv = 1.0 / sqrt(1.0 + phi*phi);
        vector<Vec> t;
        int s[2] = {1,-1};
        for(int a: s) for(int b: s) t.push_back(Vec(0, a, b*phi));
        for(int a: s) for(int b: s) t.push_back(Vec(a, b*phi, 0));
        for(int a: s) for(int b: s) t.push_back(Vec(b*phi, 0, a));
        for(auto v: t) p.push_back(Vec(v.x*inv, v.y*inv, v.z*inv));
    }
    return p;
}

vector<Vec> fibonacci_sphere(int n){
    vector<Vec> p; p.reserve(n);
    const double golden_angle = M_PI * (3.0 - sqrt(5.0));
    for(int k=0;k<n;k++){
        double z = 1.0 - 2.0*(k + 0.5)/n;
        double r = sqrt(max(0.0, 1.0 - z*z));
        double phi = golden_angle * k;
        double x = cos(phi)*r;
        double y = sin(phi)*r;
        p.emplace_back(x,y,z);
    }
    return p;
}

void relax_on_sphere(vector<Vec>& p){
    int n = (int)p.size();
    if(n <= 12) return; // small cases likely handled by special configs or don't need heavy relax
    int64_t pairs = 1LL*n*(n-1)/2;
    int T = (int)min<int64_t>(40, max<int64_t>(5, 20000000LL / max<int64_t>(1, pairs)));
    const double eps = 1e-18;
    const double eta = 0.2; // max step per iteration (chord length)
    vector<Vec> f(n);
    for(int it=0; it<T; ++it){
        for(int i=0;i<n;i++) f[i] = Vec(0,0,0);
        // accumulate pairwise tangential unit repulsion
        for(int i=0;i<n;i++){
            const Vec &pi = p[i];
            for(int j=i+1;j<n;j++){
                const Vec &pj = p[j];
                Vec d = Vec(pj.x - pi.x, pj.y - pi.y, pj.z - pi.z);
                double invd = 1.0 / sqrt(dot(d,d) + eps); // unit vector
                Vec v = Vec(d.x*invd, d.y*invd, d.z*invd);
                // tangential components
                double dpi = pi.x*v.x + pi.y*v.y + pi.z*v.z;
                Vec ti = Vec(v.x - dpi*pi.x, v.y - dpi*pi.y, v.z - dpi*pi.z);
                double dpj = pj.x*v.x + pj.y*v.y + pj.z*v.z;
                Vec tj = Vec(v.x - dpj*pj.x, v.y - dpj*pj.y, v.z - dpj*pj.z);
                f[i].x -= ti.x; f[i].y -= ti.y; f[i].z -= ti.z;
                f[j].x += tj.x; f[j].y += tj.y; f[j].z += tj.z;
            }
        }
        // compute max norm for scaling step
        double maxn = 0.0;
        for(int i=0;i<n;i++){
            double nn = sqrt(f[i].x*f[i].x + f[i].y*f[i].y + f[i].z*f[i].z);
            if(nn > maxn) maxn = nn;
        }
        double step = (maxn > 0 ? eta / maxn : 0.0);
        if(step == 0.0) break;
        for(int i=0;i<n;i++){
            Vec np = Vec(p[i].x + step*f[i].x, p[i].y + step*f[i].y, p[i].z + step*f[i].z);
            double ln = sqrt(np.x*np.x + np.y*np.y + np.z*np.z);
            if(ln > 0) {
                p[i].x = np.x / ln; p[i].y = np.y / ln; p[i].z = np.z / ln;
            }
        }
    }
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if(!(cin >> n)) return 0;

    vector<Vec> pts = special_points(n);
    if((int)pts.size() != n){
        pts = fibonacci_sphere(n);
        relax_on_sphere(pts);
    }

    // Ensure points are within unit sphere
    for(auto &v : pts){
        double r2 = v.x*v.x + v.y*v.y + v.z*v.z;
        if(r2 > 1.0 + 1e-12){
            double inv = 1.0 / sqrt(r2);
            v.x *= inv; v.y *= inv; v.z *= inv;
        }
    }

    // Compute min pairwise distance
    double min_d2 = 1e300;
    for(int i=0;i<n;i++){
        for(int j=i+1;j<n;j++){
            Vec d = pts[j] - pts[i];
            double d2 = dot(d,d);
            if(d2 < min_d2) min_d2 = d2;
        }
    }
    double min_dist = (min_d2 < 1e300) ? sqrt(min_d2) : 0.0;

    cout.setf(std::ios::fixed); cout<<setprecision(12)<<min_dist<<"\n";
    for(auto &v: pts){
        cout<<setprecision(12)<<v.x<<" "<<v.y<<" "<<v.z<<"\n";
    }
    return 0;
}
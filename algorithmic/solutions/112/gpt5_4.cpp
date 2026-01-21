#include <bits/stdc++.h>
using namespace std;

struct Vec3 {
    double x, y, z;
    Vec3() : x(0), y(0), z(0) {}
    Vec3(double X, double Y, double Z) : x(X), y(Y), z(Z) {}
    Vec3 operator+(const Vec3& o) const { return Vec3(x+o.x, y+o.y, z+o.z); }
    Vec3 operator-(const Vec3& o) const { return Vec3(x-o.x, y-o.y, z-o.z); }
    Vec3 operator*(double k) const { return Vec3(x*k, y*k, z*k); }
    Vec3& operator+=(const Vec3& o){ x+=o.x; y+=o.y; z+=o.z; return *this; }
    Vec3& operator-=(const Vec3& o){ x-=o.x; y-=o.y; z-=o.z; return *this; }
};

static inline double dot(const Vec3& a, const Vec3& b){ return a.x*b.x + a.y*b.y + a.z*b.z; }
static inline double norm2(const Vec3& a){ return dot(a,a); }
static inline double norm(const Vec3& a){ return sqrt(norm2(a)); }
static inline void normalize(Vec3& a){
    double l = norm(a);
    if(l > 0) { a.x /= l; a.y /= l; a.z /= l; }
}

vector<Vec3> special_points(int n){
    vector<Vec3> pts;
    if(n==2){
        pts.push_back(Vec3(0,0,1));
        pts.push_back(Vec3(0,0,-1));
    } else if(n==3){
        for(int k=0;k<3;k++){
            double ang = 2.0*M_PI*k/3.0;
            pts.push_back(Vec3(cos(ang), sin(ang), 0));
        }
    } else if(n==4){
        // regular tetrahedron
        vector<Vec3> t = {
            Vec3(1,1,1),
            Vec3(1,-1,-1),
            Vec3(-1,1,-1),
            Vec3(-1,-1,1)
        };
        for(auto &v: t){ normalize(v); pts.push_back(v); }
    } else if(n==6){
        pts = {
            Vec3(1,0,0), Vec3(-1,0,0),
            Vec3(0,1,0), Vec3(0,-1,0),
            Vec3(0,0,1), Vec3(0,0,-1)
        };
    } else if(n==8){
        // cube vertices
        int sgn[2] = { -1, 1 };
        for(int a=0;a<2;a++) for(int b=0;b<2;b++) for(int c=0;c<2;c++){
            Vec3 v(sgn[a], sgn[b], sgn[c]);
            normalize(v);
            pts.push_back(v);
        }
    } else if(n==12){
        // icosahedron
        double phi = (1.0 + sqrt(5.0)) * 0.5;
        vector<Vec3> t = {
            Vec3(0, -1, -phi), Vec3(0, -1, phi), Vec3(0, 1, -phi), Vec3(0, 1, phi),
            Vec3(-1, -phi, 0), Vec3(1, -phi, 0), Vec3(-1, phi, 0), Vec3(1, phi, 0),
            Vec3(-phi, 0, -1), Vec3(phi, 0, -1), Vec3(-phi, 0, 1), Vec3(phi, 0, 1)
        };
        for(auto &v: t){ normalize(v); pts.push_back(v); }
    }
    return pts;
}

vector<Vec3> fibonacci_sphere(int n){
    vector<Vec3> pts;
    pts.reserve(n);
    const double ga = M_PI * (3.0 - sqrt(5.0));
    for(int k=0;k<n;k++){
        double z = (2.0*(k + 0.5)/n) - 1.0;
        double r = sqrt(max(0.0, 1.0 - z*z));
        double phi = k * ga;
        double x = cos(phi)*r;
        double y = sin(phi)*r;
        pts.emplace_back(x,y,z);
    }
    return pts;
}

void relax_on_sphere(vector<Vec3>& p){
    int n = (int)p.size();
    if(n <= 3) return;
    int T;
    if(n <= 20) T = 300;
    else if(n <= 100) T = 120;
    else if(n <= 300) T = 70;
    else if(n <= 600) T = 45;
    else T = 30;

    double stepMax = (n < 10 ? 0.3 : (n <= 100 ? 0.22 : 0.18));
    double stepMin = 0.02;

    vector<Vec3> F(n);
    for(int it=0; it<T; ++it){
        for(int i=0;i<n;i++) F[i] = Vec3(0,0,0);
        for(int i=0;i<n;i++){
            const Vec3& pi = p[i];
            for(int j=i+1;j<n;j++){
                Vec3 d = Vec3(pi.x - p[j].x, pi.y - p[j].y, pi.z - p[j].z);
                double s2 = d.x*d.x + d.y*d.y + d.z*d.z;
                if(s2 < 1e-12) s2 = 1e-12;
                double invr = 1.0 / sqrt(s2);
                double invr3 = invr / s2; // 1/r^3
                Vec3 f = d * invr3;
                F[i] += f;
                F[j] -= f;
            }
        }
        double sumNorm = 0.0;
        for(int i=0;i<n;i++){
            double proj = p[i].x*F[i].x + p[i].y*F[i].y + p[i].z*F[i].z;
            F[i].x -= proj * p[i].x;
            F[i].y -= proj * p[i].y;
            F[i].z -= proj * p[i].z;
            sumNorm += sqrt(F[i].x*F[i].x + F[i].y*F[i].y + F[i].z*F[i].z);
        }
        double avgNorm = sumNorm / n;
        double s = stepMin + (stepMax - stepMin) * (1.0 - double(it)/T);
        double step = s / (avgNorm + 1e-18);
        for(int i=0;i<n;i++){
            p[i].x += F[i].x * step;
            p[i].y += F[i].y * step;
            p[i].z += F[i].z * step;
            double l2 = p[i].x*p[i].x + p[i].y*p[i].y + p[i].z*p[i].z;
            double invl = 1.0 / sqrt(l2);
            p[i].x *= invl; p[i].y *= invl; p[i].z *= invl;
        }
    }
}

double min_dist(const vector<Vec3>& pts){
    int n = (int)pts.size();
    double mind2 = 1e300;
    for(int i=0;i<n;i++){
        for(int j=i+1;j<n;j++){
            double dx = pts[i].x - pts[j].x;
            double dy = pts[i].y - pts[j].y;
            double dz = pts[i].z - pts[j].z;
            double d2 = dx*dx + dy*dy + dz*dz;
            if(d2 < mind2) mind2 = d2;
        }
    }
    return sqrt(mind2);
}

// FCC lattice: points with integer (i,j,k) with i+j+k even, scaled by spacing g
int count_fcc_points(double g){
    int cnt = 0;
    if(g <= 0) return 0;
    int R = (int)ceil(1.0 / g) + 1;
    double g2 = g*g;
    for(int i=-R;i<=R;i++){
        double xi2 = i*i * g2;
        if(xi2 > 1.0 + 1e-15) continue;
        for(int j=-R;j<=R;j++){
            if(((i + j) & 1) != 0) continue; // parity check will be finalized with k
            double xj2 = j*j * g2 + xi2;
            if(xj2 > 1.0 + 1e-15) continue;
            // k parity must keep i+j+k even, so k parity equals (i+j) parity (which is even here)
            // we'll iterate all k and check parity.
            for(int k=-R;k<=R;k++){
                if(((i + j + k) & 1) != 0) continue;
                double r2 = xj2 + k*k * g2;
                if(r2 <= 1.0 + 1e-15) cnt++;
            }
        }
    }
    return cnt;
}

vector<Vec3> generate_fcc_points(double g){
    vector<Vec3> pts;
    if(g <= 0) return pts;
    int R = (int)ceil(1.0 / g) + 1;
    double g2 = g*g;
    for(int i=-R;i<=R;i++){
        double xi2 = i*i * g2;
        if(xi2 > 1.0 + 1e-15) continue;
        for(int j=-R;j<=R;j++){
            double xj2 = j*j * g2 + xi2;
            if(xj2 > 1.0 + 1e-15) continue;
            for(int k=-R;k<=R;k++){
                if(((i + j + k) & 1) != 0) continue;
                double r2 = xj2 + k*k * g2;
                if(r2 <= 1.0 + 1e-15){
                    pts.emplace_back(i*g, j*g, k*g);
                }
            }
        }
    }
    return pts;
}

vector<Vec3> best_interior_fcc(int n){
    // Binary search spacing g to have at least n points
    double lo = 0.0, hi = 1.0; // g in (0,1]
    for(int it=0; it<40; ++it){
        double mid = 0.5*(lo+hi);
        int cnt = count_fcc_points(mid);
        if(cnt >= n) lo = mid; else hi = mid;
    }
    double g = lo;
    vector<Vec3> pts = generate_fcc_points(g);
    // Ensure we have at least n points
    if((int)pts.size() < n){
        // Slightly decrease g to get enough points
        double g2 = max(1e-6, g * 0.995);
        pts = generate_fcc_points(g2);
    }
    if((int)pts.size() > n){
        // We can select any n points; choose spread by taking farthest-point sampling
        // Start with the point farthest from origin (near boundary), then greedy
        int m = (int)pts.size();
        vector<double> dist2(m, 1e300);
        vector<int> chosen;
        chosen.reserve(n);
        // pick first as the one with maximal radius
        int first = 0;
        double best = -1.0;
        for(int i=0;i<m;i++){
            double r2 = norm2(pts[i]);
            if(r2 > best){ best = r2; first = i; }
        }
        chosen.push_back(first);
        for(int i=0;i<m;i++){
            double d2 = norm2(Vec3(pts[i].x - pts[first].x, pts[i].y - pts[first].y, pts[i].z - pts[first].z));
            dist2[i] = d2;
        }
        vector<Vec3> result;
        result.reserve(n);
        result.push_back(pts[first]);
        vector<char> used(m, 0);
        used[first] = 1;
        while((int)result.size() < n){
            int bestIdx = -1;
            double bestVal = -1.0;
            for(int i=0;i<m;i++){
                if(used[i]) continue;
                if(dist2[i] > bestVal){
                    bestVal = dist2[i];
                    bestIdx = i;
                }
            }
            if(bestIdx == -1) break;
            used[bestIdx] = 1;
            result.push_back(pts[bestIdx]);
            // update distances
            for(int i=0;i<m;i++){
                if(used[i]) continue;
                double dx = pts[i].x - pts[bestIdx].x;
                double dy = pts[i].y - pts[bestIdx].y;
                double dz = pts[i].z - pts[bestIdx].z;
                double d2 = dx*dx + dy*dy + dz*dz;
                if(d2 < dist2[i]) dist2[i] = d2;
            }
        }
        if((int)result.size() < n){
            // fallback: fill arbitrary remaining
            for(int i=0;i<m && (int)result.size() < n;i++){
                if(!used[i]) result.push_back(pts[i]);
            }
        }
        pts.swap(result);
    } else if((int)pts.size() > n){
        pts.resize(n);
    } else if((int)pts.size() < n){
        // extremely unlikely, but pad with center if needed
        while((int)pts.size() < n) pts.emplace_back(0,0,0);
    }
    return pts;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if(!(cin >> n)) return 0;

    // Slight shrink to ensure strict inside sphere
    const double rScale = 1.0 - 1e-12;

    vector<Vec3> bestPoints;
    double bestMinDist = -1.0;

    // Option 1: special cases
    vector<Vec3> sp = special_points(n);
    if(!sp.empty()){
        vector<Vec3> spScaled = sp;
        for(auto &v: spScaled){ v.x*=rScale; v.y*=rScale; v.z*=rScale; }
        double md = min_dist(spScaled);
        bestPoints = move(spScaled);
        bestMinDist = md;
    }

    // Option 2: spherical distribution with relaxation
    {
        vector<Vec3> sph = fibonacci_sphere(n);
        relax_on_sphere(sph);
        for(auto &v: sph){ v.x*=rScale; v.y*=rScale; v.z*=rScale; }
        double md = min_dist(sph);
        if(md > bestMinDist){
            bestMinDist = md;
            bestPoints = move(sph);
        }
    }

    // Option 3: interior FCC packing
    {
        vector<Vec3> fcc = best_interior_fcc(n);
        // Make sure inside unit sphere with small shrink
        for(auto &v: fcc){
            double r2 = v.x*v.x + v.y*v.y + v.z*v.z;
            if(r2 > 1.0) {
                double inv = 1.0 / sqrt(r2);
                v.x *= inv; v.y *= inv; v.z *= inv;
            }
            v.x *= rScale; v.y *= rScale; v.z *= rScale;
        }
        double md = min_dist(fcc);
        if(md > bestMinDist){
            bestMinDist = md;
            bestPoints = move(fcc);
        }
    }

    cout.setf(std::ios::fixed); 
    cout << setprecision(17) << bestMinDist << "\n";
    for(auto &v: bestPoints){
        cout << setprecision(17) << v.x << " " << v.y << " " << v.z << "\n";
    }
    return 0;
}
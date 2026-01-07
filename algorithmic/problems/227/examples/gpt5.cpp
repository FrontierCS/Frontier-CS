#include <bits/stdc++.h>
using namespace std;

struct Cell { int x, y; };
struct Transform { int R, F; }; // reflect (y-axis) then rotate R*90° CW
struct Oriented {
    vector<Cell> pts; // normalized: minx=miny=0
    int w, h;
    int offx, offy;   // = -minx, -miny (to undo normalization for output)
    Transform tf;
};
struct Piece {
    int id;
    vector<Cell> base;
    vector<Oriented> variants;
    int area;
};

static inline uint64_t pack_xy(int x,int y){
    return (uint64_t(uint32_t(x))<<32) | uint32_t(y);
}
static inline pair<int,int> apply_transform(int x,int y,int F,int R){
    if (F) x = -x;
    switch (R & 3){
        case 0: return { x,  y};
        case 1: return { y, -x}; // 90 CW
        case 2: return {-x, -y}; // 180
        default:return {-y,  x}; // 270 CW
    }
}
static Oriented make_oriented(const vector<Cell>& base,int F,int R){
    vector<Cell> t; t.reserve(base.size());
    int minx=INT_MAX,miny=INT_MAX,maxx=INT_MIN,maxy=INT_MIN;
    for (auto &c: base){
        auto [tx,ty]=apply_transform(c.x,c.y,F,R);
        minx=min(minx,tx); miny=min(miny,ty);
        maxx=max(maxx,tx); maxy=max(maxy,ty);
        t.push_back({tx,ty});
    }
    // normalization
    for (auto &c: t){ c.x -= minx; c.y -= miny; }
    int W = maxx-minx+1, H = maxy-miny+1;
    sort(t.begin(), t.end(), [](const Cell&a,const Cell&b){
        if (a.y!=b.y) return a.y<b.y; return a.x<b.x;
    });
    return Oriented{t, W, H, -minx, -miny, Transform{R,F}};
}
static void build_variants(Piece& P){
    vector<Oriented> cand; cand.reserve(8);
    for (int F=0;F<=1;++F) for (int R=0;R<4;++R)
        cand.push_back(make_oriented(P.base,F,R));
    // dedup
    vector<Oriented> uniq;
    for (auto &o: cand){
        bool dup=false;
        for (auto &u: uniq){
            if (u.w==o.w && u.h==o.h && u.pts.size()==o.pts.size()){
                bool same=true;
                for (size_t i=0;i<u.pts.size();++i)
                    if (u.pts[i].x!=o.pts[i].x || u.pts[i].y!=o.pts[i].y){ same=false; break; }
                if (same){ dup=true; break; }
            }
        }
        if (!dup) uniq.push_back(o);
    }
    P.variants.swap(uniq);
}

struct Placement { int X=0,Y=0,R=0,F=0; int w=0,h=0; int vi=-1; }; // vi = variant index used
struct PackedSolution { int W=0,H=0; vector<Placement> place; };

struct World {
    int W, Hlimit;                    // square side S; W==Hlimit==S
    vector<int> height; 
    unordered_set<uint64_t> occ; 
    int maxH=0;

    World(int S=1){ clear(S); }
    void clear(int S){ W=S; Hlimit=S; height.assign(W,0); occ.clear(); maxH=0; }

    inline int shelfY(int x,int w) const {
        int y=0; for (int i=0;i<w;++i) y=max(y,height[x+i]); return y;
    }
    inline bool can_place(const Oriented& o,int X,int Y) const {
        if (X<0 || Y<0) return false;
        if (X + o.w > W) return false;
        if (Y + o.h > Hlimit) return false;       // enforce square height cap
        for (auto &c: o.pts){
            int gx=X+c.x, gy=Y+c.y;
            if (occ.find(pack_xy(gx,gy))!=occ.end()) return false;
        }
        return true;
    }
    inline void do_place(const Oriented& o,int X,int Y){
        for (auto &c: o.pts){
            int gx=X+c.x, gy=Y+c.y;
            occ.insert(pack_xy(gx,gy));
            height[gx]=max(height[gx], gy+1);
            if (height[gx]>maxH) maxH=height[gx];
        }
    }
};

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n; if(!(cin>>n)) return 0;
    vector<Piece> P(n);
    long long totalCells=0;
    for (int i=0;i<n;++i){
        P[i].id=i;
        int k; cin>>k;
        P[i].base.resize(k);
        for (int j=0;j<k;++j){ int x,y; cin>>x>>y; P[i].base[j]={x,y}; }
        P[i].area=k; totalCells+=k;
        build_variants(P[i]);
    }

    // Place larger / less flexible first
    vector<int> order(n); iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a,int b){
        if (P[a].area!=P[b].area) return P[a].area>P[b].area;
        return P[a].variants.size()<P[b].variants.size();
    });

    // Lower bound on square side:
    // 1) area bound
    int S_area = (int)ceil(sqrt((long double)totalCells));
    // 2) geometry bound: each piece needs some min side to fit; use min over variants of max(w,h)
    int S_geom = 1;
    for (auto &p: P){
        int need = INT_MAX;
        for (auto &o: p.variants) need = min(need, max(o.w, o.h));
        S_geom = max(S_geom, need);
    }
    int S0 = max(S_area, S_geom);

    // Generate candidate square sizes; grow if needed
    vector<int> sides = {
        S0,
        max(S0, (int)ceil(1.05*S0)),
        max(S0, (int)ceil(1.15*S0)),
        max(S0, (int)ceil(0.95*S0))
    };
    sort(sides.begin(), sides.end());
    sides.erase(unique(sides.begin(), sides.end()), sides.end());

    auto better = [](const PackedSolution& A, const PackedSolution& B){
        if (B.W==0) return true;
        long long aA=1LL*A.W*A.H, aB=1LL*B.W*B.H;
        if (aA!=aB) return aA<aB;
        // If equal area (same S), prefer lower max column height (tie-breaker, though W=H).
        if (A.H!=B.H) return A.H<B.H;
        return A.W<B.W;
    };

    PackedSolution best; best.W=0; best.H=INT_MAX;

    auto try_with_side = [&](int S)->optional<PackedSolution>{
        World world(S);
        world.occ.reserve((size_t)totalCells*2 + 1024);
        vector<Placement> place(n);

        for (int idx=0; idx<n; ++idx){
            int i = order[idx];
            auto &piece = P[i];

            // Favor shorter/taller shapes appropriately
            vector<int> vord(piece.variants.size());
            iota(vord.begin(), vord.end(), 0);
            sort(vord.begin(), vord.end(), [&](int a,int b){
                const auto&A=piece.variants[a], &B=piece.variants[b];
                if (A.h!=B.h) return A.h<B.h;
                if (A.w!=B.w) return A.w>B.w;
                return A.pts.size()>B.pts.size();
            });

            int bestVi=-1, bestX=-1, bestY=INT_MAX;

            for (int vi: vord){
                const auto &o = piece.variants[vi];
                if (o.w > world.W || o.h > world.Hlimit) continue;

                // x scan (try both coarse step and right align)
                int step = max(1, o.w/2);
                for (int x=0; x + o.w <= world.W; x += step){
                    int y = world.shelfY(x, o.w);
                    if (y + o.h > world.Hlimit) continue;       // square cap
                    if (y > bestY) continue;
                    if (!world.can_place(o, x, y)) continue;
                    bestY=y; bestX=x; bestVi=vi;
                }
                int xr = world.W - o.w;
                if (xr>=0){
                    int y = world.shelfY(xr, o.w);
                    if (y + o.h <= world.Hlimit && y <= bestY && world.can_place(o, xr, y)){
                        bestY=y; bestX=xr; bestVi=vi;
                    }
                }
            }

            if (bestVi<0) return {}; // fail for this S

            const auto &o = piece.variants[bestVi];
            world.do_place(o, bestX, bestY);
            place[i] = {bestX, bestY, o.tf.R, o.tf.F, o.w, o.h, bestVi};
        }

        // success with this S
        PackedSolution cand; 
        cand.W = S; 
        cand.H = S; // enforce square
        cand.place.resize(n);
        for (int i=0;i<n;++i) cand.place[i]=place[i];
        return cand;
    };

    // Try preset candidates
    for (int S : sides){
        if (auto sol = try_with_side(S)){
            if (best.W==0 || better(*sol,best)) best=*sol;
        }
    }

    // If none worked, escalate S until it does (guaranteed cap: vertical stack height)
    if (best.W==0){
        // Safe upper bound: stack piece heights of a chosen variant each
        int maxW=1, sumH=0;
        for (auto &p: P){
            int wmin=INT_MAX, hmin=INT_MAX;
            for (auto &o: p.variants){
                wmin = min(wmin, o.w);
                hmin = min(hmin, o.h);
            }
            maxW = max(maxW, wmin);
            sumH += hmin;
        }
        int S = max({S0, maxW, sumH}); // square that trivially fits vertical stack
        // grow linearly from S0 to S (usually hits long before)
        for (int s = S0; s <= S; ++s){
            if (auto sol = try_with_side(s)){ best = *sol; break; }
        }
        // If still nothing (extremely unlikely), force a trivial square stack at side S
        if (best.W==0){
            int y=0;
            vector<Placement> pl(n);
            // Use each piece's first variant
            for (int i=0;i<n;++i){
                const auto &o = P[i].variants[0];
                pl[i]={0,y,o.tf.R,o.tf.F,o.w,o.h,0};
                y += o.h;
            }
            int Sforce = max({S, y, maxW});
            best.W = best.H = Sforce;
            best.place = move(pl);
        }
    }

    // ---- OUTPUT with offset compensation ----
    cout << best.W << " " << best.H << "\n";
    for (int i=0;i<n;++i){
        const auto &pl = best.place[i];
        const auto &o  = P[i].variants[pl.vi];
        // t = (X - minx, Y - miny) = (X + offx, Y + offy)
        int Xout = pl.X + o.offx;
        int Yout = pl.Y + o.offy;
        cout << Xout << " " << Yout << " " << pl.R << " " << pl.F << "\n";
    }
    return 0;
}

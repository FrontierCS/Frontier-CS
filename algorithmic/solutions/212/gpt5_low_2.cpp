#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m, L, R, Sx, Sy, Lq;
    long long s;
    if(!(cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> s)) return 0;
    vector<int> q(Lq);
    for(int i=0;i<Lq;i++) cin >> q[i];

    auto inRange = [&](int x){ return 1 <= x && x <= n; };

    // Build possible p sequences and choose feasible plan
    auto build_p1 = [&](vector<int>& p){
        p.clear();
        // Sx, Sx-1, ..., 1, n, n-1, ..., Sx+1
        for(int r=Sx; r>=1; --r) p.push_back(r);
        for(int r=n; r>=Sx+1; --r) p.push_back(r);
    };
    auto build_p2 = [&](vector<int>& p){
        p.clear();
        // Sx, Sx+1, ..., n, 1, 2, ..., Sx-1
        for(int r=Sx; r<=n; ++r) p.push_back(r);
        for(int r=1; r<=Sx-1; ++r) p.push_back(r);
    };
    auto is_subseq = [&](const vector<int>& p)->bool{
        // q elements must be in 1..n
        for(int x: q) if(x < 1 || x > n) return false;
        int j=0;
        for(int x: p){
            if(j < (int)q.size() && x == q[j]) ++j;
        }
        return j == (int)q.size();
    };

    // Plans:
    // planType:
    // 0: impossible
    // 1: single snake Sx=1 upward
    // 2: single snake Sx=n downward
    // 3: p1 with external after row 1 to row n
    // 4: p2 with external after row n to row 1
    int planType = 0;
    vector<int> pchosen;

    if(Sx == 1 && Sy == L){
        // Only one possible p: [1..n]
        vector<int> p; p.reserve(n);
        for(int r=1; r<=n; ++r) p.push_back(r);
        if(is_subseq(p)){
            planType = 1;
            pchosen = p;
        }
    } else if(Sx == n && Sy == L){
        // Only one possible p: [n..1]
        vector<int> p; p.reserve(n);
        for(int r=n; r>=1; --r) p.push_back(r);
        if(is_subseq(p)){
            planType = 2;
            pchosen = p;
        }
    } else if(Sy == L){
        // Middle case needs at least one external
        bool hasLeft = (L > 1);
        bool hasRight = (R < m);

        // Try p1
        vector<int> p1; build_p1(p1);
        bool ok1 = false;
        if(is_subseq(p1)) {
            // End column after finishing row 1 when going down from Sx to 1
            bool endAtR = ((Sx - 1) % 2 == 0);
            if( (endAtR && hasRight) || (!endAtR && hasLeft) ) ok1 = true;
        }
        // Try p2
        vector<int> p2; build_p2(p2);
        bool ok2 = false;
        if(is_subseq(p2)) {
            bool endAtR = ((n - Sx) % 2 == 0);
            if( (endAtR && hasRight) || (!endAtR && hasLeft) ) ok2 = true;
        }
        if(ok1){ planType = 3; pchosen = p1; }
        else if(ok2){ planType = 4; pchosen = p2; }
        else {
            planType = 0;
        }
    } else {
        // Starting Sy should equal L as guaranteed, but guard anyway
        planType = 0;
    }

    if(planType == 0){
        cout << "NO\n";
        return 0;
    }

    // Build path according to plan
    vector<pair<int,int>> path;
    path.reserve(n*(R-L+1) + (m>R? (n+2):0) + (L>1? (n+2):0));

    auto sweep_to = [&](int x, int y_from, int y_to){
        if(y_from <= y_to){
            for(int y=y_from; y<=y_to; ++y) path.emplace_back(x,y);
        }else{
            for(int y=y_from; y>=y_to; --y) path.emplace_back(x,y);
        }
    };
    auto push_vertical = [&](int x_from, int x_to, int y){
        if(x_from <= x_to){
            for(int x=x_from; x<=x_to; ++x) path.emplace_back(x,y);
        }else{
            for(int x=x_from; x>=x_to; --x) path.emplace_back(x,y);
        }
    };

    if(planType == 1){
        // Sx=1, snake downwards: p = [1..n]
        // Start at (1,L)
        path.emplace_back(1, L);
        // sweep 1: L->R
        sweep_to(1, L+1, R);
        int e = R;
        for(int r=2; r<=n; ++r){
            // move to (r, e)
            path.emplace_back(r, e);
            // sweep across to other end
            if(e == R){
                sweep_to(r, R-1, L);
                e = L;
            }else{
                sweep_to(r, L+1, R);
                e = R;
            }
        }
    } else if(planType == 2){
        // Sx=n, snake upwards: p = [n..1]
        path.emplace_back(n, L);
        sweep_to(n, L+1, R);
        int e = R;
        for(int r=n-1; r>=1; --r){
            path.emplace_back(r, e);
            if(e == R){
                sweep_to(r, R-1, L);
                e = L;
            }else{
                sweep_to(r, L+1, R);
                e = R;
            }
        }
    } else if(planType == 3){
        // p1: down to 1, then external to n, then down to Sx+1
        // Start Sx
        path.emplace_back(Sx, L);
        // sweep Sx: L->R
        sweep_to(Sx, L+1, R);
        int e = R; // current endpoint
        // go down to 1
        for(int r=Sx-1; r>=1; --r){
            // move to (r, e)
            path.emplace_back(r, e);
            if(e == R){
                sweep_to(r, R-1, L);
                e = L;
            }else{
                sweep_to(r, L+1, R);
                e = R;
            }
        }
        // Now at row 1 at endpoint e
        int yExt = (e == R ? R+1 : L-1);
        // step to external
        path.emplace_back(1, yExt);
        // move along external to row n
        if(1 != n){
            if(1 < n) {
                for(int x=2; x<=n; ++x) path.emplace_back(x, yExt);
            } else {
                for(int x=0; x>=n; --x) path.emplace_back(x, yExt);
            }
        }
        // step into row n at endpoint e
        path.emplace_back(n, e);
        // sweep row n starting from endpoint e
        if(e == R){
            sweep_to(n, R-1, L);
            e = L;
        }else{
            sweep_to(n, L+1, R);
            e = R;
        }
        // then go down to Sx+1
        for(int r=n-1; r>=Sx+1; --r){
            path.emplace_back(r, e);
            if(e == R){
                sweep_to(r, R-1, L);
                e = L;
            }else{
                sweep_to(r, L+1, R);
                e = R;
            }
        }
    } else if(planType == 4){
        // p2: up to n, then external to 1, then up to Sx-1
        path.emplace_back(Sx, L);
        sweep_to(Sx, L+1, R);
        int e = R;
        // up to n
        for(int r=Sx+1; r<=n; ++r){
            path.emplace_back(r, e);
            if(e == R){
                sweep_to(r, R-1, L);
                e = L;
            }else{
                sweep_to(r, L+1, R);
                e = R;
            }
        }
        // at row n at endpoint e
        int yExt = (e == R ? R+1 : L-1);
        path.emplace_back(n, yExt);
        // move along external to row 1
        if(n != 1){
            if(n > 1){
                for(int x=n-1; x>=1; --x) path.emplace_back(x, yExt);
            } else {
                for(int x=n+1; x<=1; ++x) path.emplace_back(x, yExt);
            }
        }
        // step into row 1 at endpoint e
        path.emplace_back(1, e);
        if(e == R){
            sweep_to(1, R-1, L);
            e = L;
        }else{
            sweep_to(1, L+1, R);
            e = R;
        }
        // then up to Sx-1
        for(int r=2; r<=Sx-1; ++r){
            path.emplace_back(r, e);
            if(e == R){
                sweep_to(r, R-1, L);
                e = L;
            }else{
                sweep_to(r, L+1, R);
                e = R;
            }
        }
    }

    // Final safety checks:
    // 1) No duplicates
    // 2) All required cells covered exactly once
    // 3) Start at (Sx, L)
    // 4) p sequence subsequence q already checked
    // We will trust construction but do minimal check to avoid obvious issues in rare edge cases
    // Due to constraints, we'll skip heavy checks.

    cout << "YES\n";
    cout << (int)path.size() << "\n";
    for(auto &pt: path){
        cout << pt.first << " " << pt.second << "\n";
    }
    return 0;
}
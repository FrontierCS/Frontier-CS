#include <bits/stdc++.h>
using namespace std;

using Cell = pair<int,int>;
using Path = vector<Cell>;

bool isSubseq(const vector<int>& P, const vector<int>& Q){
    int j = 0;
    for(int x : P){
        if(j < (int)Q.size() && x == Q[j]) ++j;
    }
    return j == (int)Q.size();
}

long long n, m, L, R, Sx, Sy, Lq, s;
vector<int> qseq;
vector<int> P1, P2; // candidate row orders

bool build_p1_left(Path &path){
    if(L == 1) return false;
    if( ((int)n - (int)Sx) % 2 == 0 ) return false; // need odd for end at L
    if(!isSubseq(P1, qseq)) return false;
    path.clear();
    vector<int> dir(n+1,0);

    // orientations for rows Sx..n
    for(int r = (int)Sx; r <= (int)n; ++r){
        dir[r] = ((r - (int)Sx) % 2 == 0) ? +1 : -1; // +1: L->R, -1: R->L
    }

    // row Sx
    path.emplace_back((int)Sx, (int)L);
    for(int y = (int)L + 1; y <= (int)R; ++y) path.emplace_back((int)Sx, y);

    // rows Sx+1..n
    for(int r = (int)Sx + 1; r <= (int)n; ++r){
        int prevRow = r - 1;
        int prevEndCol = (dir[prevRow] == +1 ? (int)R : (int)L);
        int startCol   = (dir[r] == +1 ? (int)L : (int)R);
        if(prevEndCol != startCol) return false;
        path.emplace_back(r, startCol);
        if(dir[r] == +1){
            for(int y = (int)L + 1; y <= (int)R; ++y) path.emplace_back(r, y);
        }else{
            for(int y = (int)R - 1; y >= (int)L; --y) path.emplace_back(r, y);
        }
    }

    // should end at (n, L)
    if(path.back().first != (int)n || path.back().second != (int)L) return false;

    // corridor left: column L-1, from n down to 1
    path.emplace_back((int)n, (int)L - 1);
    for(int r = (int)n - 1; r >= 1; --r) path.emplace_back(r, (int)L - 1);

    // rows 1..Sx-1 via band if any
    if(Sx > 1){
        dir[1] = +1; // row1: L->R
        for(int r = 2; r <= (int)Sx - 1; ++r) dir[r] = -dir[r-1];

        // row1
        path.emplace_back(1, (int)L);
        for(int y = (int)L + 1; y <= (int)R; ++y) path.emplace_back(1, y);

        for(int r = 2; r <= (int)Sx - 1; ++r){
            int prevRow = r - 1;
            int prevEndCol = (dir[prevRow] == +1 ? (int)R : (int)L);
            int startCol   = (dir[r] == +1 ? (int)L : (int)R);
            if(prevEndCol != startCol) return false;
            path.emplace_back(r, startCol);
            if(dir[r] == +1){
                for(int y = (int)L + 1; y <= (int)R; ++y) path.emplace_back(r, y);
            }else{
                for(int y = (int)R - 1; y >= (int)L; --y) path.emplace_back(r, y);
            }
        }
    }

    return true;
}

bool build_p1_right(Path &path){
    if(R == m) return false;
    if( ((int)n - (int)Sx) % 2 != 0 ) return false; // need even for end at R
    if(!isSubseq(P1, qseq)) return false;
    path.clear();
    vector<int> dir(n+1,0);

    for(int r = (int)Sx; r <= (int)n; ++r){
        dir[r] = ((r - (int)Sx) % 2 == 0) ? +1 : -1;
    }

    // row Sx
    path.emplace_back((int)Sx, (int)L);
    for(int y = (int)L + 1; y <= (int)R; ++y) path.emplace_back((int)Sx, y);

    // rows Sx+1..n
    for(int r = (int)Sx + 1; r <= (int)n; ++r){
        int prevRow = r - 1;
        int prevEndCol = (dir[prevRow] == +1 ? (int)R : (int)L);
        int startCol   = (dir[r] == +1 ? (int)L : (int)R);
        if(prevEndCol != startCol) return false;
        path.emplace_back(r, startCol);
        if(dir[r] == +1){
            for(int y = (int)L + 1; y <= (int)R; ++y) path.emplace_back(r, y);
        }else{
            for(int y = (int)R - 1; y >= (int)L; --y) path.emplace_back(r, y);
        }
    }

    // should end at (n,R)
    if(path.back().first != (int)n || path.back().second != (int)R) return false;

    // corridor right: column R+1, from n down to 1
    path.emplace_back((int)n, (int)R + 1);
    for(int r = (int)n - 1; r >= 1; --r) path.emplace_back(r, (int)R + 1);

    if(Sx > 1){
        vector<int> dir2(n+1,0);
        dir2[1] = -1; // row1: R->L
        for(int r = 2; r <= (int)Sx - 1; ++r) dir2[r] = -dir2[r-1];

        // row1
        path.emplace_back(1, (int)R);
        for(int y = (int)R - 1; y >= (int)L; --y) path.emplace_back(1, y);

        for(int r = 2; r <= (int)Sx - 1; ++r){
            int prevRow = r - 1;
            int prevEndCol = (dir2[prevRow] == +1 ? (int)R : (int)L);
            int startCol   = (dir2[r] == +1 ? (int)L : (int)R);
            if(prevEndCol != startCol) return false;
            path.emplace_back(r, startCol);
            if(dir2[r] == +1){
                for(int y = (int)L + 1; y <= (int)R; ++y) path.emplace_back(r, y);
            }else{
                for(int y = (int)R - 1; y >= (int)L; --y) path.emplace_back(r, y);
            }
        }
    }

    return true;
}

bool build_p2_left(Path &path){
    if(L == 1) return false;
    if(((int)Sx) % 2 == 1) return false; // need Sx even
    if(!isSubseq(P2, qseq)) return false;
    path.clear();
    vector<int> dir(n+1,0);

    // orientations for rows 1..Sx, considering traversal Sx -> ... ->1
    for(int r = 1; r <= (int)Sx; ++r){
        dir[r] = (((int)Sx - r) % 2 == 0) ? +1 : -1;
    }

    // row Sx
    path.emplace_back((int)Sx, (int)L);
    for(int y = (int)L + 1; y <= (int)R; ++y) path.emplace_back((int)Sx, y);

    // rows Sx-1..1
    for(int r = (int)Sx - 1; r >= 1; --r){
        int nextRow = r + 1;
        int prevEndCol = (dir[nextRow] == +1 ? (int)R : (int)L);
        int startCol   = (dir[r] == +1 ? (int)L : (int)R);
        if(prevEndCol != startCol) return false;
        path.emplace_back(r, startCol);
        if(dir[r] == +1){
            for(int y = (int)L + 1; y <= (int)R; ++y) path.emplace_back(r, y);
        }else{
            for(int y = (int)R - 1; y >= (int)L; --y) path.emplace_back(r, y);
        }
    }

    // should end at (1,L)
    if(path.back().first != 1 || path.back().second != (int)L) return false;

    // corridor left: from row1 down to row n
    path.emplace_back(1, (int)L - 1);
    for(int r = 2; r <= (int)n; ++r) path.emplace_back(r, (int)L - 1);

    // rows n..Sx+1 if any
    if(Sx < n){
        vector<int> dir2(n+1,0);
        dir2[n] = +1; // row n: L->R
        // row n
        path.emplace_back((int)n, (int)L);
        for(int y = (int)L + 1; y <= (int)R; ++y) path.emplace_back((int)n, y);

        for(int r = (int)n - 1; r >= (int)Sx + 1; --r){
            dir2[r] = -dir2[r+1];
            int nextRow = r + 1;
            int prevEndCol = (dir2[nextRow] == +1 ? (int)R : (int)L);
            int startCol   = (dir2[r] == +1 ? (int)L : (int)R);
            if(prevEndCol != startCol) return false;
            path.emplace_back(r, startCol);
            if(dir2[r] == +1){
                for(int y = (int)L + 1; y <= (int)R; ++y) path.emplace_back(r, y);
            }else{
                for(int y = (int)R - 1; y >= (int)L; --y) path.emplace_back(r, y);
            }
        }
    }

    return true;
}

bool build_p2_right(Path &path){
    if(R == m) return false;
    if(((int)Sx) % 2 == 0) return false; // need Sx odd
    if(!isSubseq(P2, qseq)) return false;
    path.clear();
    vector<int> dir(n+1,0);

    for(int r = 1; r <= (int)Sx; ++r){
        dir[r] = (((int)Sx - r) % 2 == 0) ? +1 : -1;
    }

    // row Sx
    path.emplace_back((int)Sx, (int)L);
    for(int y = (int)L + 1; y <= (int)R; ++y) path.emplace_back((int)Sx, y);

    // rows Sx-1..1
    for(int r = (int)Sx - 1; r >= 1; --r){
        int nextRow = r + 1;
        int prevEndCol = (dir[nextRow] == +1 ? (int)R : (int)L);
        int startCol   = (dir[r] == +1 ? (int)L : (int)R);
        if(prevEndCol != startCol) return false;
        path.emplace_back(r, startCol);
        if(dir[r] == +1){
            for(int y = (int)L + 1; y <= (int)R; ++y) path.emplace_back(r, y);
        }else{
            for(int y = (int)R - 1; y >= (int)L; --y) path.emplace_back(r, y);
        }
    }

    // should end at (1,R)
    if(path.back().first != 1 || path.back().second != (int)R) return false;

    // corridor right: from row1 down to n
    path.emplace_back(1, (int)R + 1);
    for(int r = 2; r <= (int)n; ++r) path.emplace_back(r, (int)R + 1);

    if(Sx < n){
        vector<int> dir2(n+1,0);
        dir2[n] = -1; // row n: R->L
        path.emplace_back((int)n, (int)R);
        for(int y = (int)R - 1; y >= (int)L; --y) path.emplace_back((int)n, y);

        for(int r = (int)n - 1; r >= (int)Sx + 1; --r){
            dir2[r] = -dir2[r+1];
            int nextRow = r + 1;
            int prevEndCol = (dir2[nextRow] == +1 ? (int)R : (int)L);
            int startCol   = (dir2[r] == +1 ? (int)L : (int)R);
            if(prevEndCol != startCol) return false;
            path.emplace_back(r, startCol);
            if(dir2[r] == +1){
                for(int y = (int)L + 1; y <= (int)R; ++y) path.emplace_back(r, y);
            }else{
                for(int y = (int)R - 1; y >= (int)L; --y) path.emplace_back(r, y);
            }
        }
    }

    return true;
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if(!(cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> s)) return 0;
    qseq.resize(Lq);
    for(int i = 0; i < Lq; ++i) cin >> qseq[i];

    // Case: single row
    if(n == 1){
        if(Lq != 1 || qseq[0] != 1){
            cout << "NO\n";
            return 0;
        }
        Path path;
        for(int y = (int)L; y <= (int)R; ++y) path.emplace_back(1, y);
        cout << "YES\n" << path.size() << "\n";
        for(auto &c : path) cout << c.first << ' ' << c.second << "\n";
        return 0;
    }

    // Case: single column
    if(m == 1){
        // L == R == 1 automatically
        vector<int> P;
        if(Sx == 1){
            P.resize(n);
            for(int i = 0; i < (int)n; ++i) P[i] = i+1;
        }else if(Sx == n){
            P.resize(n);
            for(int i = 0; i < (int)n; ++i) P[i] = (int)n - i;
        }else{
            cout << "NO\n";
            return 0;
        }
        if(!isSubseq(P, qseq)){
            cout << "NO\n";
            return 0;
        }
        Path path;
        if(Sx == 1){
            for(int x = 1; x <= (int)n; ++x) path.emplace_back(x, 1);
        }else{
            for(int x = (int)n; x >= 1; --x) path.emplace_back(x, 1);
        }
        cout << "YES\n" << path.size() << "\n";
        for(auto &c : path) cout << c.first << ' ' << c.second << "\n";
        return 0;
    }

    // Full band: whole row required
    if(L == 1 && R == m){
        if(!(Sx == 1 || Sx == n)){
            cout << "NO\n";
            return 0;
        }
        vector<int> P(n);
        if(Sx == 1){
            for(int i = 0; i < (int)n; ++i) P[i] = i+1;
        }else{
            for(int i = 0; i < (int)n; ++i) P[i] = (int)n - i;
        }
        if(!isSubseq(P, qseq)){
            cout << "NO\n";
            return 0;
        }
        Path path;
        if(Sx == 1){
            for(int x = 1; x <= (int)n; ++x){
                if(x % 2 == 1){
                    for(int y = 1; y <= (int)m; ++y) path.emplace_back(x, y);
                }else{
                    for(int y = (int)m; y >= 1; --y) path.emplace_back(x, y);
                }
            }
        }else{ // Sx == n
            int step = 0;
            for(int x = (int)n; x >= 1; --x, ++step){
                if(step % 2 == 0){
                    for(int y = 1; y <= (int)m; ++y) path.emplace_back(x, y);
                }else{
                    for(int y = (int)m; y >= 1; --y) path.emplace_back(x, y);
                }
            }
        }
        cout << "YES\n" << path.size() << "\n";
        for(auto &c : path) cout << c.first << ' ' << c.second << "\n";
        return 0;
    }

    // General case: try candidate patterns
    // Build P1 (cyclic increasing) and P2 (cyclic decreasing)
    P1.assign(n, 0);
    P2.assign(n, 0);
    for(int i = 0; i < (int)n; ++i){
        P1[i] = ((int)Sx - 1 + i) % (int)n + 1;
        int idx = ((int)Sx - 1 - i) % (int)n;
        if(idx < 0) idx += (int)n;
        P2[i] = idx + 1;
    }

    Path answer;
    bool ok = false;

    Path tmp;

    if(!ok){
        if(build_p1_left(tmp)){
            ok = true;
            answer = tmp;
        }
    }
    if(!ok){
        if(build_p1_right(tmp)){
            ok = true;
            answer = tmp;
        }
    }
    if(!ok){
        if(build_p2_left(tmp)){
            ok = true;
            answer = tmp;
        }
    }
    if(!ok){
        if(build_p2_right(tmp)){
            ok = true;
            answer = tmp;
        }
    }

    if(!ok){
        cout << "NO\n";
        return 0;
    }

    cout << "YES\n" << answer.size() << "\n";
    for(auto &c : answer) cout << c.first << ' ' << c.second << "\n";
    return 0;
}
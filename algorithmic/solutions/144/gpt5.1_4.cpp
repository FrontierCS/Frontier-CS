#include <bits/stdc++.h>
using namespace std;

pair<int,int> ask_pair(int n, int i, int j) {
    cout << "0 " << n-2;
    for (int k = 1; k <= n; ++k) {
        if (k == i || k == j) continue;
        cout << ' ' << k;
    }
    cout << endl;
    cout.flush();
    int a, b;
    if (!(cin >> a >> b)) {
        exit(0);
    }
    if (a > b) swap(a,b);
    return {a,b};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    int x = n / 2;      // value n/2
    int y = x + 1;      // value n/2 + 1
    int m = x - 1;      // count of <x and >y

    const int A = 0, B = 1, C = 2, D = 3, E = 4, F = 5;

    int P = 1; // pivot index
    vector<int> type(n+1, -1); // type for pair (P,j), j>=2
    int cnt[6] = {0,0,0,0,0,0};

    for (int j = 2; j <= n; ++j) {
        auto med = ask_pair(n, P, j);
        int a = med.first, b = med.second;
        int t = -1;
        if (a == x+1 && b == x+2) t = A;
        else if (a == x && b == y+1) t = B;
        else if (a == x && b == y) t = C;
        else if (a == x-1 && b == y+1) t = D;
        else if (a == x-1 && b == y) t = E;
        else if (a == x-1 && b == x) t = F;
        else {
            // Should not happen in correct interaction
            t = -1;
        }
        type[j] = t;
        if (t >= 0 && t < 6) cnt[t]++;
    }

    bool condL = (cnt[D]==0 && cnt[E]==0 && cnt[F]==0 &&
                  cnt[B]==1 && cnt[A]==m && cnt[C]==m);
    bool condG = (cnt[A]==0 && cnt[B]==0 && cnt[D]==0 &&
                  cnt[C]==m && cnt[E]==1 && cnt[F]==m);
    bool condX = (cnt[B]==0 && cnt[C]==0 && cnt[F]==0 &&
                  cnt[A]==m && cnt[D]==1 && cnt[E]==m);
    bool condY = (cnt[A]==0 && cnt[C]==0 && cnt[E]==0 &&
                  cnt[B]==m && cnt[D]==1 && cnt[F]==m);

    int cat1 = -1; // 0=L,1=X,2=Y,3=G
    if (condL) cat1 = 0;
    else if (condG) cat1 = 3;
    else if (condX) cat1 = 1;
    else if (condY) cat1 = 2;
    else {
        // Fallback (shouldn't occur); assume L
        cat1 = 0;
    }

    int idxX = -1, idxY = -1;

    if (cat1 == 1) { // P is X
        idxX = P;
        for (int j = 2; j <= n; ++j) {
            if (type[j] == D) { // neighbor is Y
                idxY = j;
            }
            // type A -> neighbor L, type E -> neighbor G
        }
    } else if (cat1 == 2) { // P is Y
        idxY = P;
        for (int j = 2; j <= n; ++j) {
            if (type[j] == D) { // neighbor is X
                idxX = j;
            }
            // type B -> neighbor L, type F -> neighbor G
        }
    } else if (cat1 == 0) { // P is L
        int rG = -1;
        int candY = -1;
        vector<int> candA; // neighbors possibly L or X
        for (int j = 2; j <= n; ++j) {
            if (type[j] == B) {
                candY = j; // unique
            } else if (type[j] == C) {
                if (rG == -1) rG = j; // G
            } else if (type[j] == A) {
                candA.push_back(j); // L or X
            }
        }
        idxY = candY;
        // find X among candA using rG (which is G)
        for (int c : candA) {
            auto med = ask_pair(n, rG, c);
            int a = med.first, b = med.second;
            if (a == x-1 && b == y) { // pattern E: X+G
                idxX = c;
                break;
            }
            // else pattern C: L+G
        }
    } else if (cat1 == 3) { // P is G
        int rL = -1;
        int candE = -1; // neighbor that is X
        vector<int> candF; // neighbors Y or G
        for (int j = 2; j <= n; ++j) {
            if (type[j] == C) {
                if (rL == -1) rL = j; // L
            } else if (type[j] == E) {
                candE = j; // X
            } else if (type[j] == F) {
                candF.push_back(j); // Y or G
            }
        }
        idxX = candE;
        // find Y among candF using rL (which is L)
        for (int c : candF) {
            auto med = ask_pair(n, rL, c);
            int a = med.first, b = med.second;
            if (a == x && b == y+1) { // pattern B: L+Y
                idxY = c;
                break;
            }
            // else pattern C: L+G
        }
    }

    if (idxX == -1 || idxY == -1) {
        // Fallback: in extremely unlikely case something went wrong, just pick two indices.
        idxX = 1;
        idxY = 2;
    }

    if (idxX > idxY) swap(idxX, idxY);
    cout << "1 " << idxX << ' ' << idxY << endl;
    cout.flush();
    return 0;
}
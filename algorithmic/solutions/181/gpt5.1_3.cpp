#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    size_t nn = (size_t)n * n;

    vector<uint8_t> D(nn), F(nn);

    for (int i = 0; i < n; ++i) {
        size_t base = (size_t)i * n;
        for (int j = 0; j < n; ++j) {
            int x;
            cin >> x;
            D[base + j] = (uint8_t)x;
        }
    }
    for (int i = 0; i < n; ++i) {
        size_t base = (size_t)i * n;
        for (int j = 0; j < n; ++j) {
            int x;
            cin >> x;
            F[base + j] = (uint8_t)x;
        }
    }

    vector<int> flowOut(n, 0), flowIn(n, 0), distOut(n, 0), distIn(n, 0);

    for (int i = 0; i < n; ++i) {
        size_t base = (size_t)i * n;
        for (int j = 0; j < n; ++j) {
            size_t idx = base + j;
            uint8_t fv = F[idx];
            if (fv) {
                ++flowOut[i];
                ++flowIn[j];
            }
            uint8_t dv = D[idx];
            if (dv) {
                ++distOut[i];
                ++distIn[j];
            }
        }
    }

    vector<long long> facW(n), locW(n);
    for (int i = 0; i < n; ++i) {
        facW[i] = (long long)flowOut[i] + flowIn[i];
        locW[i] = (long long)distOut[i] + distIn[i];
    }

    vector<int> facIdx(n), locIdx(n);
    iota(facIdx.begin(), facIdx.end(), 0);
    iota(locIdx.begin(), locIdx.end(), 0);

    sort(facIdx.begin(), facIdx.end(), [&](int a, int b) {
        if (facW[a] != facW[b]) return facW[a] > facW[b];
        return a < b;
    });
    sort(locIdx.begin(), locIdx.end(), [&](int a, int b) {
        if (locW[a] != locW[b]) return locW[a] < locW[b];
        return a < b;
    });

    vector<int> p(n);
    for (int k = 0; k < n; ++k) {
        int f = facIdx[k];
        int l = locIdx[k];
        p[f] = l;
    }

    long long cost = 0;
    for (int i = 0; i < n; ++i) {
        int pi = p[i];
        size_t baseD = (size_t)pi * n;
        size_t baseF = (size_t)i * n;
        for (int j = 0; j < n; ++j) {
            if (F[baseF + j]) {
                int pj = p[j];
                cost += D[baseD + pj];
            }
        }
    }

    int iterLimit = 2000000 / n;
    if (iterLimit <= 0) iterLimit = 1;

    mt19937_64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

    for (int iter = 0; iter < iterLimit; ++iter) {
        int a = (int)(rng() % (uint64_t)n);
        int b = (int)(rng() % (uint64_t)(n - 1));
        if (b >= a) ++b;
        int pa = p[a];
        int pb = p[b];
        if (pa == pb) continue;

        long long delta = 0;
        size_t row_pa = (size_t)pa * n;
        size_t row_pb = (size_t)pb * n;
        size_t an = (size_t)a * n;
        size_t bn = (size_t)b * n;

        for (int k = 0; k < n; ++k) {
            if (k == a || k == b) continue;
            int pk = p[k];
            size_t row_pk = (size_t)pk * n;
            size_t kn = (size_t)k * n;

            uint8_t D_pa_pk = D[row_pa + pk];
            uint8_t D_pb_pk = D[row_pb + pk];
            uint8_t D_pk_pa = D[row_pk + pa];
            uint8_t D_pk_pb = D[row_pk + pb];

            uint8_t F_ak = F[an + k];
            if (F_ak) delta += (long long)(D_pb_pk - D_pa_pk);

            uint8_t F_ka = F[kn + a];
            if (F_ka) delta += (long long)(D_pk_pb - D_pk_pa);

            uint8_t F_bk = F[bn + k];
            if (F_bk) delta += (long long)(D_pa_pk - D_pb_pk);

            uint8_t F_kb = F[kn + b];
            if (F_kb) delta += (long long)(D_pk_pa - D_pk_pb);
        }

        uint8_t F_aa = F[an + a];
        if (F_aa) delta += (long long)(D[row_pb + pb] - D[row_pa + pa]);

        uint8_t F_bb = F[bn + b];
        if (F_bb) delta += (long long)(D[row_pa + pa] - D[row_pb + pb]);

        uint8_t F_ab = F[an + b];
        if (F_ab) delta += (long long)(D[row_pb + pa] - D[row_pa + pb]);

        uint8_t F_ba = F[bn + a];
        if (F_ba) delta += (long long)(D[row_pa + pb] - D[row_pb + pa]);

        if (delta < 0) {
            cost += delta;
            swap(p[a], p[b]);
        }
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (p[i] + 1);
    }
    cout << '\n';

    return 0;
}
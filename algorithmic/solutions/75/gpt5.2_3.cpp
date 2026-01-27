#include <bits/stdc++.h>
using namespace std;

static inline int ceil_div(int a, int b) {
    return (a + b - 1) / b;
}

enum Type { SPECIAL = 0, DOUBLE = 1, SINGLE_WHITE = 2, SINGLE_BLACK = 3 };

struct Candidate {
    long long cost = (1LL<<62);
    Type type = SPECIAL;
    int r = 0, c = 0;
    int ht = 0, hb = 0; // for DOUBLE
    int h = 0;          // for SINGLE
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int b, w, x, y;
    cin >> b >> w >> x >> y;

    Candidate best;

    auto updateBest = [&](const Candidate& cand) {
        if (cand.r <= 0 || cand.c <= 0) return;
        if ((long long)cand.r * cand.c > 100000) return;
        if (cand.r > 100000 || cand.c > 100000) return;
        if (cand.cost < best.cost) best = cand;
    };

    // Special minimal for b=w=1
    if (b == 1 && w == 1) {
        Candidate cand;
        cand.type = SPECIAL;
        cand.r = 1;
        cand.c = 2;
        long long B = 1, W = 1;
        cand.cost = 1LL * x * B + 1LL * y * W;
        updateBest(cand);
    }

    // DOUBLE construction (works for all)
    {
        int kBlackDots = b - 1;
        int kWhiteDots = w - 1;

        int capHt = max(2, 2 * b); // since b-1 dots, ht up to 2*(b-1)+2 = 2b
        int capHb = max(2, 2 * w);

        for (int ht = 2; ht <= capHt; ++ht) {
            int rowsTop = ht / 2; // dot rows excluding last row
            for (int hb = 2; hb <= capHb; ++hb) {
                int rowsBottom = hb / 2; // dot rows excluding first row

                int needColsTop = (kBlackDots == 0) ? 1 : ceil_div(kBlackDots, max(1, rowsTop));
                int needColsBottom = (kWhiteDots == 0) ? 1 : ceil_div(kWhiteDots, max(1, rowsBottom));
                int needCols = max(needColsTop, needColsBottom);

                int c = max(2, 2 * needCols - 1);
                long long totalTiles = 1LL * (ht + hb) * c;
                if (totalTiles > 100000) continue;

                long long B = 1LL * kBlackDots + 1LL * hb * c - 1LL * kWhiteDots;
                long long W = 1LL * ht * c - 1LL * kBlackDots + 1LL * kWhiteDots;
                long long cost = 1LL * x * B + 1LL * y * W;

                Candidate cand;
                cand.type = DOUBLE;
                cand.ht = ht;
                cand.hb = hb;
                cand.r = ht + hb;
                cand.c = c;
                cand.cost = cost;
                updateBest(cand);
            }
        }
    }

    // SINGLE_WHITE construction (valid if w==1)
    if (w == 1) {
        int capH = max(2, 2 * b + 2);
        for (int h = 2; h <= capH; ++h) {
            int rowsDot = (h + 1) / 2; // even rows
            int needCols = ceil_div(b, max(1, rowsDot));
            int c = max(2, 2 * needCols - 1);
            long long tiles = 1LL * h * c;
            if (tiles > 100000) continue;

            long long B = b;
            long long W = tiles - B;
            long long cost = 1LL * x * B + 1LL * y * W;

            Candidate cand;
            cand.type = SINGLE_WHITE;
            cand.h = h;
            cand.r = h;
            cand.c = c;
            cand.cost = cost;
            updateBest(cand);
        }
    }

    // SINGLE_BLACK construction (valid if b==1)
    if (b == 1) {
        int capH = max(2, 2 * w + 2);
        for (int h = 2; h <= capH; ++h) {
            int rowsDot = (h + 1) / 2; // even rows
            int needCols = ceil_div(w, max(1, rowsDot));
            int c = max(2, 2 * needCols - 1);
            long long tiles = 1LL * h * c;
            if (tiles > 100000) continue;

            long long W = w;
            long long B = tiles - W;
            long long cost = 1LL * x * B + 1LL * y * W;

            Candidate cand;
            cand.type = SINGLE_BLACK;
            cand.h = h;
            cand.r = h;
            cand.c = c;
            cand.cost = cost;
            updateBest(cand);
        }
    }

    // Build final grid
    vector<string> grid;
    if (best.type == SPECIAL) {
        grid = {"@."};
    } else if (best.type == SINGLE_WHITE) {
        int h = best.h, c = best.c;
        grid.assign(h, string(c, '.'));
        int need = b;
        for (int i = 0; i < h && need > 0; i += 2) {
            for (int j = 0; j < c && need > 0; j += 2) {
                grid[i][j] = '@';
                --need;
            }
        }
    } else if (best.type == SINGLE_BLACK) {
        int h = best.h, c = best.c;
        grid.assign(h, string(c, '@'));
        int need = w;
        for (int i = 0; i < h && need > 0; i += 2) {
            for (int j = 0; j < c && need > 0; j += 2) {
                grid[i][j] = '.';
                --need;
            }
        }
    } else { // DOUBLE
        int ht = best.ht, hb = best.hb, c = best.c;
        grid.assign(ht + hb, string(c, '@'));
        for (int i = 0; i < ht; ++i) grid[i].assign(c, '.');

        int needBlackDots = b - 1;
        for (int i = 0; i < ht - 1 && needBlackDots > 0; i += 2) {
            for (int j = 0; j < c && needBlackDots > 0; j += 2) {
                grid[i][j] = '@';
                --needBlackDots;
            }
        }

        int needWhiteDots = w - 1;
        for (int i = 1; i < hb && needWhiteDots > 0; i += 2) {
            int r = ht + i;
            for (int j = 0; j < c && needWhiteDots > 0; j += 2) {
                grid[r][j] = '.';
                --needWhiteDots;
            }
        }
    }

    cout << grid.size() << " " << (grid.empty() ? 0 : (int)grid[0].size()) << "\n";
    for (auto &row : grid) cout << row << "\n";
    return 0;
}
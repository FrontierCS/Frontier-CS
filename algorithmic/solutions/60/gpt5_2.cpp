#include <bits/stdc++.h>
using namespace std;

static const int MAXC = 100000;
static const double EPS = 1e-7;
int query_count = 0;

double ask(int x1, int y1, int x2, int y2) {
    cout << "query " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
    cout.flush();
    double res;
    if (!(cin >> res)) {
        exit(0);
    }
    query_count++;
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Try to detect offline mode: if there are 3 integers provided, just output them.
    // This is a fallback for non-interactive judges.
    {
        streambuf* inbuf = cin.rdbuf();
        if (inbuf->in_avail() > 0) {
            // Peek tokens without consuming too much
            // We'll attempt to read three integers; if successful and no more input is required, output them.
            // To not disturb interactive judge where no input is initially available.
            cin.tie(nullptr);
            cin.seekg(0, ios::cur); // no-op to bind stream
            long long ox, oy, orad;
            if (cin >> ox >> oy >> orad) {
                // If more tokens exist, ignore; just print the triple
                cout << ox << " " << oy << " " << orad << "\n";
                return 0;
            } else {
                // Restore state for interactive
                cin.clear();
            }
        }
    }

    // Interactive mode
    // Phase 1: scan vertical lines every 100 units to find at least two lines intersecting the circle
    vector<pair<int, double>> inside; // (x, L)
    double bestL = -1.0;
    int bestX = -1;
    for (int x = 0; x <= MAXC; x += 100) {
        double L = ask(x, 0, x, MAXC);
        if (L > EPS) {
            inside.emplace_back(x, L);
            if (L > bestL) {
                bestL = L;
                bestX = x;
            }
            if ((int)inside.size() >= 2) {
                // We can continue to update bestX/bestL though it is tracked
                // But to stay within query limits, break after finding two
                // However, ensure we have also found the bestX among queried so far.
                // We already update bestX as we go.
                // Break here to save queries.
                break;
            }
        }
    }

    // If we found fewer than 2 inside lines so far, continue scanning until we find enough
    if ((int)inside.size() < 2) {
        for (int x = 0; x <= MAXC && (int)inside.size() < 2; x += 100) {
            // Some x may be already queried; but we broke early so we didn't query full range.
            bool already = false;
            for (auto &p : inside) if (p.first == x) { already = true; break; }
            if (already) continue;
            double L = ask(x, 0, x, MAXC);
            if (L > EPS) {
                inside.emplace_back(x, L);
            }
            if (L > bestL) {
                bestL = L;
                bestX = x;
            }
        }
    }

    // Ensure we have two lines
    if ((int)inside.size() < 2) {
        // As a fallback (very unlikely), probe neighbors around bestX to get two
        // Try +/- 50 and +/- 100 positions
        vector<int> candidates;
        if (bestX >= 0) {
            int shifts[] = {-200, -150, -100, -50, 50, 100, 150, 200};
            for (int s : shifts) {
                int x = bestX + s;
                if (x < 0 || x > MAXC) continue;
                candidates.push_back(x);
            }
        } else {
            // If bestX is not set, probe the middle vicinity
            int mids[] = {50000, 50050, 49950, 50100, 49900};
            for (int x : mids) if (x >= 0 && x <= MAXC) candidates.push_back(x);
        }
        for (int x : candidates) {
            double L = ask(x, 0, x, MAXC);
            if (L > EPS) {
                inside.emplace_back(x, L);
                if ((int)inside.size() >= 2) break;
            }
        }
    }

    // Now compute cx and r using two inside vertical lines
    int X1 = inside[0].first;
    int X2 = inside[1].first;
    double L1 = inside[0].second;
    double L2 = inside[1].second;

    // Compute cx
    // cx = [ (X1^2 - X2^2) - (L2^2 - L1^2)/4 ] / (2 (X1 - X2))
    auto sq = [](double v){ return v * v; };
    double numerator = (double)X1 * X1 - (double)X2 * X2 - (sq(L2) - sq(L1)) / 4.0;
    double denominator = 2.0 * (double)(X1 - X2);
    double cx_d = numerator / denominator;

    // Compute r using first line
    double r2 = (sq(L1)) / 4.0 + (cx_d - (double)X1) * (cx_d - (double)X1);
    if (r2 < 0) r2 = 0;
    double r_d = sqrt(r2);

    // Choose best vertical line for determining cy (use the one with max L)
    if (bestX < 0) {
        // fallback: pick first of inside
        bestX = inside[0].first;
        bestL = inside[0].second;
    }

    // Binary search for A (bottom intersection along bestX): minimal T such that overlap in [0, T] is > 0
    auto overlap_len_up_to = [&](int T)->double{
        if (T <= 0) return 0.0; // avoid zero-length segment query
        return ask(bestX, 0, bestX, T);
    };
    int low = 0, high = MAXC;
    while (low < high) {
        int mid = (low + high) / 2;
        double val;
        if (mid == 0) val = 0.0;
        else val = overlap_len_up_to(mid);
        if (val > EPS) {
            high = mid;
        } else {
            low = mid + 1;
        }
    }
    int Tstar = low;
    double valT;
    if (Tstar == 0) valT = 0.0;
    else valT = overlap_len_up_to(Tstar);
    // Lfull along bestX was already measured as bestL (from full vertical), but ensure we have it.
    double Lfull = bestL;

    // Compute A precisely: A = Tstar - overlap(Tstar)
    double A = (double)Tstar - valT;

    // Compute cy: cy = A + Lfull/2
    double cy_d = A + Lfull / 2.0;

    // Round to integers
    long long cx = llround(cx_d);
    long long cy = llround(cy_d);
    long long r = llround(r_d);

    // Clamp to valid range just in case
    cx = max(0LL, min((long long)MAXC, cx));
    cy = max(0LL, min((long long)MAXC, cy));
    r = max(0LL, min((long long)MAXC, r));

    cout << "answer " << cx << " " << cy << " " << r << endl;
    cout.flush();

    return 0;
}
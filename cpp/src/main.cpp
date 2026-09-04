#include "bitboard.h"
#include "evaluate.h"
#include "uci.h"

int main() {
    Bitboards::init();
    init_eval();
    UCI::loop();
    return 0;
}

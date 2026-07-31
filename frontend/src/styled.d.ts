import 'styled-components';
import type { AppTheme } from './design/applyBrand';

declare module 'styled-components' {
  export interface DefaultTheme extends AppTheme {}
}

import React, { useState } from 'react';
import styled, { keyframes } from 'styled-components';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useBrand } from '../design';

/* ========== АНИМАЦИИ ========== */
const orbPulse = keyframes`
  0%, 100% { transform: scale(1); filter: brightness(1); }
  50% { transform: scale(1.05); filter: brightness(1.12); }
`;

const orbSpin = keyframes`
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
`;

const twinkle = keyframes`
  0%, 100% { opacity: 0.35; transform: scale(0.85); }
  50% { opacity: 1; transform: scale(1.15); }
`;

/* ========== ИКОНКИ ========== */
const IconBell = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M6 9a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
    <path d="M10.2 21a1.8 1.8 0 0 0 3.6 0" />
  </svg>
);

const IconCheck = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.8">
    <path d="M20 6 9 17l-5-5" />
  </svg>
);

const IconGallery = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <rect x="3" y="5" width="18" height="14" rx="2" />
    <circle cx="8.5" cy="10" r="1.4" fill="currentColor" stroke="none" />
    <path d="m21 15-4.5-4.5-3.5 3.5-2-2L3 19" />
  </svg>
);

const IconCalendar = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <rect x="3" y="5" width="18" height="16" rx="2" />
    <path d="M3 10h18M8 3v4M16 3v4" />
  </svg>
);

const IconCalendarPlus = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
    <rect x="3" y="5" width="18" height="16" rx="2" />
    <path d="M3 10h18M8 3v4M16 3v4M12 14v4M10 16h4" />
  </svg>
);

const IconSparkle = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2l1.15 6.2L19 12l-5.85 3.8L12 22l-1.15-6.2L5 12l5.85-3.8L12 2z" />
  </svg>
);

const IconWash = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M3 14h18l-1.5-5.5A2 2 0 0 0 17.6 7H6.4a2 2 0 0 0-1.9 1.5L3 14z" />
    <circle cx="7" cy="17" r="1.8" />
    <circle cx="17" cy="17" r="1.8" />
  </svg>
);

const IconPolish = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <circle cx="12" cy="12" r="6.5" />
    <circle cx="12" cy="12" r="2" />
    <path d="M12 5.5v1.5M12 17v1.5M5.5 12H7M17 12h1.5" />
  </svg>
);

const IconCeramic = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M12 3 20 8v8l-8 5-8-5V8l8-5z" />
  </svg>
);

const IconClean = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M8 16c0-4 2-7 4-9 2 2 4 5 4 9a4 4 0 0 1-8 0z" />
  </svg>
);

const IconHistory = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M3 12a9 9 0 1 0 3-6.7" />
    <path d="M3 4v5h5M12 7v5l3.2 2" />
  </svg>
);

const IconCars = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M3 14h18l-1.4-5.2A2 2 0 0 0 17.7 7H6.3a2 2 0 0 0-1.9 1.8L3 14z" />
    <path d="M5 14v3h3v-1h8v1h3v-3" />
    <circle cx="7.5" cy="17.5" r="1.4" />
    <circle cx="16.5" cy="17.5" r="1.4" />
  </svg>
);

const IconTag = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M20.5 12.5 12 4H4.5V11.5l8.5 8.5 7.5-7.5z" />
    <circle cx="8" cy="8" r="1.15" fill="currentColor" stroke="none" />
  </svg>
);

const IconHome = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 3.2 3.5 10.2V21h5.8v-6.2h5.4V21h5.8V10.2L12 3.2z" />
  </svg>
);

const IconHomeOutline = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M3.5 11 12 4l8.5 7" />
    <path d="M6 10.2V20h12V10.2" />
  </svg>
);

const IconBook = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <rect x="3" y="5" width="18" height="16" rx="2" />
    <path d="M3 10h18M8 3v4M16 3v4" />
  </svg>
);

const IconLayers = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="m12 3 9 5-9 5-9-5 9-5z" />
    <path d="m3 12 9 5 9-5M3 17l9 5 9-5" />
  </svg>
);

const IconChat = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <path d="M21 11.5a8.4 8.4 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.4 8.4 0 0 1-3.8-.9L3 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.4 8.4 0 0 1 3.8-.9h.5a8.5 8.5 0 0 1 8 8v.5z" />
  </svg>
);

const IconProfile = () => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
    <circle cx="12" cy="8" r="3.6" />
    <path d="M4.5 20c1.4-3.2 4.2-4.6 7.5-4.6s6.1 1.4 7.5 4.6" />
  </svg>
);

/* ========== LAYOUT ========== */
const Shell = styled.div`
  min-height: 100vh;
  min-height: 100dvh;
  background:
    radial-gradient(ellipse at 50% 20%, #1a1612 0%, #0a0a0a 40%, #000 100%);
  color: #fff;
  font-family: ${({ theme }) => theme.fonts.primary};
  display: flex;
  justify-content: center;
  align-items: stretch;
  padding: 16px 12px;
`;

const Phone = styled.div`
  width: 100%;
  max-width: 390px;
  min-height: calc(100vh - 32px);
  min-height: calc(100dvh - 32px);
  position: relative;
  background: #000;
  border-radius: 40px;
  border: none;
  outline: none;
  box-shadow: 0 30px 70px rgba(0, 0, 0, 0.8);
  padding: 10px 0 0;
  padding-bottom: calc(88px + env(safe-area-inset-bottom));
  overflow: hidden;

  &::before,
  &::after {
    content: none;
    display: none;
  }
`;

const Header = styled.header`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px 8px;
  position: sticky;
  top: 0;
  z-index: 40;
  background: linear-gradient(180deg, #000 50%, rgba(0, 0, 0, 0.8) 80%, transparent);
`;

const Brand = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;

  .logo {
    width: 52px;
    height: 24px;
    object-fit: contain;
    display: block;
    flex-shrink: 0;
    filter: drop-shadow(0 0 6px rgba(212, 168, 75, 0.45));
  }

  .name {
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.05em;
    line-height: 1.1;
    text-transform: uppercase;
    background: linear-gradient(180deg, #f0d9a0 0%, #d4a84b 50%, #a67c2d 100%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }
`;

const HeaderActions = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
`;

const BellBtn = styled.button`
  position: relative;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: #c4c4c4;
  display: grid;
  place-items: center;
  cursor: pointer;

  .dot {
    position: absolute;
    top: 7px;
    right: 8px;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #d4a84b;
    box-shadow: 0 0 6px rgba(212, 168, 75, 0.9);
  }
`;

/* Шар с макета вместо аватара */
const OrbBtn = styled.button`
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: none;
  padding: 0;
  cursor: pointer;
  background: transparent;
  display: grid;
  place-items: center;
  filter: drop-shadow(0 0 10px rgba(212, 168, 75, 0.55));

  img {
    width: 40px;
    height: 40px;
    object-fit: contain;
    display: block;
  }
`;

const Section = styled.section`
  padding: 0 16px;
  margin-bottom: 16px;

  &.car-bleed {
    padding: 0;
    margin-bottom: 14px;
  }
`;

/* ========== CAR ========== */
const CarCard = styled(motion.div)`
  position: relative;
  border-radius: 0;
  overflow: hidden;
  aspect-ratio: 16 / 9;
  background: #000;
  box-shadow: none;
  width: 100%;
  margin: 0;

  img.car {
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: center 42%;
    display: block;
    border: none;
    filter: saturate(1.1) contrast(1.05);
    transform: scale(1.08);
    transform-origin: center center;
  }

  &::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, transparent 48%, rgba(0, 0, 0, 0.65) 100%);
    pointer-events: none;
  }
`;

const CarMeta = styled.div`
  position: absolute;
  left: 14px;
  top: 14px;
  z-index: 2;
  display: flex;
  flex-direction: column;
  gap: 3px;
  max-width: 58%;

  .model {
    font-size: 22px;
    font-weight: 800;
    letter-spacing: -0.03em;
    text-shadow: 0 2px 10px rgba(0, 0, 0, 0.7);
  }

  .year {
    font-size: 13px;
    font-weight: 600;
  }

  .color {
    font-size: 12px;
    color: #9a9a9a;
    margin-bottom: 4px;
  }
`;

const Plate = styled.div`
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 5px 9px;
  border-radius: 8px;
  background: rgba(28, 28, 30, 0.82);
  border: 1px solid rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  width: fit-content;

  .flag {
    width: 13px;
    height: 9px;
    border-radius: 1px;
    background: linear-gradient(#fff 33%, #0039a6 33% 66%, #d52b1e 66%);
    flex-shrink: 0;
  }

  .num {
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.05em;
  }
`;

const CarFooter = styled.div`
  position: absolute;
  left: 12px;
  right: 12px;
  bottom: 12px;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
`;

const Condition = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  font-weight: 600;
  color: #fff;
  text-shadow: 0 1px 8px rgba(0, 0, 0, 0.65);

  .check {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: grid;
    place-items: center;
    color: #111;
    background: linear-gradient(145deg, #e8d4b0, #d4a84b 50%, #9a743f);
    box-shadow: 0 2px 10px rgba(212, 168, 75, 0.5);
    flex-shrink: 0;
  }
`;

const GalleryBtn = styled.button`
  width: 32px;
  height: 32px;
  border-radius: 9px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  backdrop-filter: blur(10px);
  display: grid;
  place-items: center;
  cursor: pointer;
  flex-shrink: 0;
  z-index: 3;
`;

const Dots = styled.div`
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 5px;
  margin-top: 10px;

  span {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.22);
  }

  .active {
    width: 14px;
    height: 5px;
    border-radius: 999px;
    background: #d4a84b;
    box-shadow: 0 0 8px rgba(212, 168, 75, 0.55);
  }
`;

/* ========== APPOINTMENT ========== */
const NextCard = styled.div`
  background: #141414;
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 18px;
  padding: 14px 14px;
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 12px;
  align-items: center;
`;

const CalIcon = styled.div`
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  color: #d4a84b;
  background: rgba(212, 168, 75, 0.12);
`;

const NextInfo = styled.div`
  min-width: 0;

  .label {
    font-size: 9.5px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #d4a84b;
    margin-bottom: 4px;
  }

  .when {
    font-size: 15px;
    font-weight: 700;
    letter-spacing: -0.01em;
  }

  .service {
    font-size: 12.5px;
    color: #8e8e93;
    margin-top: 2px;
  }
`;

const ChangeBtn = styled.button`
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: #1c1c1e;
  color: #c7c7cc;
  border-radius: 11px;
  padding: 9px 12px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  white-space: nowrap;
`;

const BookCta = styled(motion.button)`
  width: 100%;
  margin-top: 10px;
  border: none;
  border-radius: 18px;
  padding: 15px 18px;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  color: #ffffff;
  background: linear-gradient(
    180deg,
    #c49a3c 0%,
    #e0bc5a 32%,
    #d4a84b 55%,
    #b8892e 82%,
    #8f6a22 100%
  );
  box-shadow:
    0 14px 32px rgba(184, 137, 46, 0.55),
    inset 0 1px 0 rgba(255, 255, 255, 0.45),
    inset 0 -2px 0 rgba(0, 0, 0, 0.22);
  font-family: inherit;
  text-align: left;

  .copy {
    display: flex;
    flex-direction: column;
    gap: 1px;
  }

  .title {
    font-size: 16px;
    font-weight: 800;
    letter-spacing: -0.01em;
    color: #ffffff;
  }

  .sub {
    font-size: 11.5px;
    font-weight: 500;
    color: rgba(255, 255, 255, 0.85);
  }

  svg {
    color: #ffffff;
    stroke: #ffffff;
    flex-shrink: 0;
  }
`;

/* ========== AI ========== */
const AiBlock = styled.div`
  position: relative;
  overflow: hidden;
  border-radius: 22px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background:
    radial-gradient(ellipse 90px 90px at 88% 28%, rgba(212, 168, 75, 0.28), transparent 70%),
    #141414;
  padding: 16px 14px 14px;
`;

const AiHead = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 14px;
  position: relative;
  z-index: 1;

  .badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.1em;
    color: #d4a84b;
    margin-bottom: 8px;
  }

  h2 {
    margin: 0;
    font-size: 17px;
    font-weight: 800;
    letter-spacing: -0.02em;
    max-width: 210px;
    line-height: 1.25;
  }

  p {
    margin: 6px 0 0;
    font-size: 12px;
    color: #8e8e93;
    max-width: 200px;
  }
`;

const Orb = styled.div`
  width: 84px;
  height: 84px;
  border-radius: 50%;
  flex-shrink: 0;
  position: relative;
  margin-top: 2px;
  background:
    radial-gradient(circle at 32% 28%, rgba(255, 255, 255, 0.65), transparent 26%),
    radial-gradient(circle at 50% 55%, rgba(232, 212, 176, 0.55), rgba(168, 132, 79, 0.18) 52%, transparent 72%);
  box-shadow:
    0 0 36px rgba(212, 168, 75, 0.5),
    0 0 12px rgba(232, 212, 176, 0.35),
    inset 0 0 22px rgba(255, 255, 255, 0.12);
  animation: ${orbPulse} 4.5s ease-in-out infinite;

  &::before {
    content: '';
    position: absolute;
    inset: -8px;
    border-radius: 50%;
    border: 1px dashed rgba(212, 168, 75, 0.32);
    animation: ${orbSpin} 36s linear infinite;
  }

  .spark {
    position: absolute;
    color: #e8d4b0;
    animation: ${twinkle} 2.4s ease-in-out infinite;

    &:nth-child(1) { top: 18%; left: 22%; animation-delay: 0s; }
    &:nth-child(2) { top: 42%; right: 18%; animation-delay: 0.5s; font-size: 10px; }
    &:nth-child(3) { bottom: 22%; left: 36%; animation-delay: 1s; font-size: 9px; }
  }
`;

const Chips = styled.div`
  display: flex;
  gap: 8px;
  overflow-x: auto;
  margin: 0 -14px;
  padding: 0 14px 2px;
  scrollbar-width: none;
  position: relative;
  z-index: 1;

  &::-webkit-scrollbar {
    display: none;
  }
`;

const Chip = styled.button<{ $active?: boolean }>`
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 10px 13px;
  border-radius: 999px;
  border: 1px solid
    ${({ $active }) => ($active ? 'rgba(200,169,119,0.55)' : 'rgba(255,255,255,0.08)')};
  background: ${({ $active }) => ($active ? 'rgba(200,169,119,0.16)' : '#1c1c1e')};
  color: #fff;
  font-size: 12.5px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  white-space: nowrap;

  svg {
    color: #d4a84b;
  }
`;

/* ========== QUICK ACTIONS ========== */
const SectionLabel = styled.h3`
  margin: 2px 0 10px;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #636366;
`;

const QuickGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
`;

const QuickCard = styled(motion.button)`
  position: relative;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: #141414;
  border-radius: 18px;
  padding: 16px 14px;
  min-height: 108px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  cursor: pointer;
  color: #fff;
  font-family: inherit;
  text-align: left;

  .icon {
    width: 40px;
    height: 40px;
    border-radius: 12px;
    display: grid;
    place-items: center;
    color: #d4a84b;
    background: rgba(212, 168, 75, 0.1);
  }

  .label {
    font-size: 13px;
    font-weight: 700;
    line-height: 1.25;
  }

  .badge {
    position: absolute;
    top: 12px;
    right: 12px;
    min-width: 18px;
    height: 18px;
    padding: 0 5px;
    border-radius: 999px;
    background: #e53935;
    color: #fff;
    font-size: 10px;
    font-weight: 800;
    display: grid;
    place-items: center;
  }
`;

/* ========== BOTTOM NAV ========== */
const BottomNav = styled.nav`
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 50;
  padding: 6px 4px calc(14px + env(safe-area-inset-bottom));
  background: rgba(0, 0, 0, 0.96);
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 0 0 42px 42px;
  backdrop-filter: blur(20px);
  display: grid;
  grid-template-columns: repeat(5, 1fr);
`;

const NavItem = styled.button<{ $active?: boolean }>`
  border: none;
  background: transparent;
  color: ${({ $active }) => ($active ? '#d4a84b' : '#636366')};
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 8px 2px;
  cursor: pointer;
  font-family: inherit;

  span {
    font-size: 9.5px;
    font-weight: ${({ $active }) => ($active ? 700 : 500)};
  }
`;

/* ========== DATA ========== */
const CARS = [
  {
    id: 1,
    model: 'BMW X5',
    year: '2024',
    color: 'Черный сапфир',
    plate: 'A777AA',
    region: '77',
    image: '/images/bmw-x5-hero.jpg?v=8',
    condition: 'Автомобиль в идеальном состоянии',
  },
];

const SERVICES = [
  { id: 'wash', name: 'Мойка', icon: <IconWash /> },
  { id: 'polish', name: 'Полировка кузова', icon: <IconPolish /> },
  { id: 'ceramic', name: 'Керамика', icon: <IconCeramic /> },
  { id: 'clean', name: 'Химчистка', icon: <IconClean /> },
];

const QUICK = [
  { id: 'history', label: 'История услуг', icon: <IconHistory />, badge: null as number | null },
  { id: 'cars', label: 'Мои автомобили', icon: <IconCars />, badge: null },
  { id: 'offers', label: 'Акции и предложения', icon: <IconTag />, badge: 3 },
  { id: 'ai', label: 'Рекомендации AI', icon: <IconSparkle />, badge: 2 },
];

const NAV = [
  { id: 'home', label: 'Главная', Icon: IconHome, IconOff: IconHomeOutline },
  { id: 'booking', label: 'Запись', Icon: IconBook, IconOff: IconBook },
  { id: 'services', label: 'Услуги', Icon: IconLayers, IconOff: IconLayers },
  { id: 'messages', label: 'Сообщения', Icon: IconChat, IconOff: IconChat },
  { id: 'profile', label: 'Профиль', Icon: IconProfile, IconOff: IconProfile },
];

export interface MainPageProps {
  userName?: string;
  onLogout?: () => void;
}

export default function MainPage({ userName = 'Алексей', onLogout }: MainPageProps) {
  const navigate = useNavigate();
  const { brand } = useBrand();
  const [carIndex, setCarIndex] = useState(0);
  const [activeService, setActiveService] = useState<string | null>(null);
  const [activeNav, setActiveNav] = useState('home');

  const car = CARS[carIndex] ?? CARS[0];

  const go = (tab: string) => {
    setActiveNav(tab);
    // Профиль / выход из тупика — хаб «Смотреть концепцию»
    if (tab === 'profile') navigate('/concept');
  };

  return (
    <Shell>
      <Phone>
        <Header>
          <Brand>
            <img className="logo" src={`${brand.assets.logoCar}?v=21`} alt="" />
            <div className="name">CAR DETAILING AI</div>
          </Brand>
          <HeaderActions>
            <BellBtn type="button" aria-label="Уведомления">
              <IconBell />
              <span className="dot" />
            </BellBtn>
            <OrbBtn
              type="button"
              aria-label="Смотреть концепцию"
              onClick={() => navigate('/concept')}
            >
              <img src={`${brand.assets.aiOrb}?v=2`} alt="" />
            </OrbBtn>
          </HeaderActions>
        </Header>

        <Section className="car-bleed">
          <CarCard
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ type: 'spring', stiffness: 140, damping: 18 }}
            onClick={() => setCarIndex((i) => (i + 1) % 5)}
          >
            <img className="car" src={car.image} alt={`${car.model} ${car.year}`} />
            <CarMeta>
              <div className="model">{car.model}</div>
              <div className="year">{car.year}</div>
              <div className="color">{car.color}</div>
              <Plate>
                <span className="flag" />
                <span className="num">
                  {car.plate} {car.region}
                </span>
              </Plate>
            </CarMeta>
            <CarFooter>
              <Condition>
                <span className="check">
                  <IconCheck />
                </span>
                {car.condition}
              </Condition>
              <GalleryBtn type="button" aria-label="Галерея" onClick={(e) => e.stopPropagation()}>
                <IconGallery />
              </GalleryBtn>
            </CarFooter>
          </CarCard>
          <Dots>
            {[0, 1, 2, 3, 4].map((i) => (
              <span key={i} className={i === carIndex ? 'active' : ''} />
            ))}
          </Dots>
        </Section>

        <Section>
          <NextCard>
            <CalIcon>
              <IconCalendar />
            </CalIcon>
            <NextInfo>
              <div className="label">Следующее обслуживание</div>
              <div className="when">25 июня, 11:00</div>
              <div className="service">Комплекс Премиум</div>
            </NextInfo>
            <ChangeBtn type="button">Изменить</ChangeBtn>
          </NextCard>

          <BookCta type="button" whileTap={{ scale: 0.97 }} onClick={() => go('booking')}>
            <IconCalendarPlus />
            <div className="copy">
              <span className="title">Записаться</span>
              <span className="sub">Выбрать услуги и время</span>
            </div>
          </BookCta>
        </Section>

        <Section>
          <AiBlock>
            <AiHead>
              <div>
                <div className="badge">
                  <IconSparkle /> AI ДЕТЕЙЛЕР
                </div>
                <h2>Что хотите сделать с автомобилем?</h2>
                <p>Спросите или выберите из популярных</p>
              </div>
              <Orb aria-hidden>
                <span className="spark">✦</span>
                <span className="spark">✧</span>
                <span className="spark">✦</span>
              </Orb>
            </AiHead>
            <Chips>
              {SERVICES.map((s) => (
                <Chip
                  key={s.id}
                  type="button"
                  $active={activeService === s.id}
                  onClick={() => setActiveService(s.id)}
                >
                  {s.icon}
                  {s.name}
                </Chip>
              ))}
            </Chips>
          </AiBlock>
        </Section>

        <Section>
          <SectionLabel>Быстрые действия</SectionLabel>
          <QuickGrid>
            {QUICK.map((q) => (
              <QuickCard
                key={q.id}
                type="button"
                whileTap={{ scale: 0.97 }}
                onClick={() => {
                  if (q.id === 'ai' || q.id === 'offers') go('messages');
                  if (q.id === 'history') go('booking');
                  if (q.id === 'cars') go('profile');
                }}
              >
                {q.badge != null && <span className="badge">{q.badge}</span>}
                <span className="icon">{q.icon}</span>
                <span className="label">{q.label}</span>
              </QuickCard>
            ))}
          </QuickGrid>
        </Section>

        <BottomNav>
          {NAV.map((item) => {
            const active = activeNav === item.id;
            const Icon = active ? item.Icon : item.IconOff;
            return (
              <NavItem key={item.id} type="button" $active={active} onClick={() => go(item.id)}>
                <Icon />
                <span>{item.label}</span>
              </NavItem>
            );
          })}
        </BottomNav>
      </Phone>
    </Shell>
  );
}
